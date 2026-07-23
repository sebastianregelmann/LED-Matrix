import time
import numpy as np
from PIL import Image, ImageDraw, ImageOps
import threading
from enum import Enum
from SpotifyClient import Client, PlaybackInfo
from ImageDriver import ImageDriver
import copy


class DisplayMode(Enum):
    DISC = 1,
    COVER = 2,
    DISC_TIME = 3,
    COVER_TIME = 4


class SpotifyImageDriver(ImageDriver): 
    spotify_client : Client

    frame_thread : threading.Thread
    stop_event : threading.Event

    #Playback info
    current_playback_info : PlaybackInfo
    last_playback_info : PlaybackInfo

    #Animation frames
    display_mode :DisplayMode
    frames :np.ndarray
    frame_index : int
    
    #Animation settings
    fps : int = 15
    rpm: float = 5
    display_error: bool = False
    change_animation_mode : bool = False
    new_display_mode : DisplayMode

    last_update : float
    playback_time_aprox : int = 0
    playback_time_last : int = 0
    lock : object

    theme_dark_track: np.ndarray = np.array([20,20,20,255], dtype=np.uint8)
    theme_progress_track: np.ndarray = np.array([90,90,90,255], dtype=np.uint8)
    theme_playhead_tip: np.ndarray = np.array([210,210,210,255], dtype=np.uint8)

    def __init__(self, request_timeout: float, display_mode:DisplayMode):
        # Call super constructor
        super().__init__()

        #create thread data
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        #Create the Spotify Client
        self.spotify_client = Client(request_timeout)
        self.display_mode = display_mode


    def start_image_driver(self):
        print("[SPOTIFY IMAGE DRIVER] Starting the spotify image driver")
        
        # start the spotify client
        self.spotify_client.start_request_thread()

        #set initial variables
        self.last_update = time.perf_counter()
        self.playback_time_last = int(time.perf_counter() * 1000)
        self.frame_index = 0
        self.current_playback_info = PlaybackInfo("Not Initialized", None, None, None, None)
        self.last_playback_info = PlaybackInfo("Not Initialized", None, None, None, None)


        #Start the thread
        self.stop_event.clear()
        self.frame_thread = threading.Thread(target=self.update_frame_loop)

        #start own thread for updating frames
        self.active = True
        self.frame_thread.start()


    def update_frame_loop(self):  
        print("[SPOTIFY IMAGE DRIVER] Started the spotify image driver")     
        
        last_tracked_progress = 0

        try:
            while not self.stop_event.is_set():
                
                # Get the current playback info
                self.current_playback_info = self.spotify_client.get_playback_info()


                #check if the display mode changed
                with self.lock:
                    if self.change_animation_mode:
                        #create the new animation
                        self.display_mode = self.new_display_mode
                        self.create_animations()
                        self.change_animation_mode = False
                        self.last_playback_info = copy.deepcopy(self.current_playback_info)
                        print("[SPOTIFY IMAGE DRIVER] Generated new Animation after mode switch")


                #check if the song id changed
                if self.current_playback_info.song_id != self.last_playback_info.song_id:
                    #create the new animation
                    self.create_animations()
                    self.last_playback_info = copy.deepcopy(self.current_playback_info)
                    self.playback_time_aprox = 0
                    print("[SPOTIFY IMAGE DRIVER] Generated new Animation after song switch")
                
                frame_interval = 1 / self.fps

                #update play time progress
                now = int(time.perf_counter() * 1000)
                elapsed = now - self.playback_time_last
                self.playback_time_last = now

                if self.current_playback_info.progress is not None:
                    if last_tracked_progress != self.current_playback_info.progress:
                        self.playback_time_aprox = self.current_playback_info.progress
                        last_tracked_progress = self.current_playback_info.progress
                    else:
                        now = int(time.perf_counter() * 1000)
                        if self.current_playback_info.is_playing:
                            if self.current_playback_info.is_playing:
                                self.playback_time_aprox += elapsed
                    
                #do nothing if Error is being displayed
                if self.display_error:
                    with self.lock: 
                        self.current_frame = self.frames[0]
                    
                    time.sleep(frame_interval / 2)
                    continue

                # Display the cover
                if self.display_mode == DisplayMode.COVER:
                    with self.lock: 
                        self.current_frame = self.frames[0]
                    
                    time.sleep(frame_interval / 2)
                    continue
                
                #Display cover with time bar
                if self.display_mode == DisplayMode.COVER_TIME:
                    cover = self.frames[0]
                    cover = self.add_time_bar(cover)
                    with self.lock: 
                        self.current_frame = cover
        
                    time.sleep(frame_interval / 2)
                    continue


                #switch the animation modes
                if self.display_mode == DisplayMode.DISC or self.display_mode == DisplayMode.DISC_TIME: 
                    now = time.perf_counter()
                    if (now - self.last_update) >= frame_interval and self.current_playback_info.is_playing:
                        self.frame_index = (self.frame_index + 1) % self.frames.shape[0]
                        self.last_update = time.perf_counter()

                    if self.display_mode == DisplayMode.DISC:
                        with self.lock: 
                            self.current_frame = self.frames[self.frame_index]
                        time.sleep(frame_interval / 2)
                        continue
                    if self.display_mode == DisplayMode.DISC_TIME:
                        
                        cover = self.frames[self.frame_index]
                        cover = self.add_time_bar(cover)

                        with self.lock: 
                            self.current_frame = cover
                        time.sleep(frame_interval / 2)
                        continue
        except Exception as e:
            print(f"[SPOTIFY IMAGE DRIVER] Error in frame thread: f{e}")
            with self.lock:
                self.current_frame = np.zeros((64,64,4), dtype=np.uint8)
                self.current_frame[...,3] = 255

        print("[SPOTIFY IMAGE DRIVER] Stopped Frame Loop")


    def create_animations(self): 
        #check if Error is displayed
        if self.current_playback_info.is_playing is None: 
            #create animation with one frame
            cover = self.ensure_rgba(self.current_playback_info.cover)
            self.frames = np.array([cover], dtype=np.uint8)
            self.display_error = True
            self.frame_index = 0
            return
        
        #Do not display error
        self.display_error = False

        cover = self.ensure_rgba(self.current_playback_info.cover)
        self.update_theme_colors(cover)
        
        # Only Cover mode
        if self.display_mode == DisplayMode.COVER:
            #create animation with one frame
            self.frames = np.array([cover], dtype=np.uint8)
            self.frame_index = 0
            return

        # Cover with Time mode
        if self.display_mode == DisplayMode.COVER_TIME:
            # load the cover
            cover = self.scaled_cover(cover)
            self.frames = np.array([cover], dtype=np.uint8)
            self.frame_index = 0
            return

        # spinning Disc
        if self.display_mode == DisplayMode.DISC:
            frames_per_rotation = int(round((self.fps * 60) / self.rpm))
            
            generated_frames = []
            for i in range(frames_per_rotation):
                angle = -(360.0 / frames_per_rotation) * i
                generated_frames.append(self.render_record(cover, angle))
            
            self.frames = np.array(generated_frames)
            self.frame_index = 0
            return

        #Scaled spinning disc
        if self.display_mode == DisplayMode.DISC_TIME:
            frames_per_rotation = int(round((self.fps * 60) / self.rpm))
            
            generated_frames = []
            for i in range(frames_per_rotation):
                angle = -(360.0 / frames_per_rotation) * i
                generated_frames.append(self.render_record_scaled(cover, angle))
            
            self.frames = np.array(generated_frames)
            self.frame_index = 0
            return


    def scaled_cover(self, image_np: np.ndarray) -> np.ndarray:
        pil_img = Image.fromarray(image_np, 'RGBA')
        scaled_pil = pil_img.resize((54, 54), Image.Resampling.LANCZOS)
        fg = np.array(scaled_pil, dtype=np.float32)

        # 2. Pad outward by 2 pixels on all sides, copying the edge pixels.
        padded_fg = np.pad(fg, ((2, 2), (2, 2), (0, 0)), mode='edge')

        # 3. Create a 58x58 grid to calculate concentric distance rings
        y = np.arange(58)
        x = np.arange(58)
        
        # Distance calculation away from the 54x54 boundary box
        dist_y = np.maximum(0, np.maximum(2 - y, y - 55))
        dist_x = np.maximum(0, np.maximum(2 - x, x - 55))
        dist = np.maximum(dist_y[:, None], dist_x[None, :]) # Ring index: 0, 1, or 2

        # 4. Map the new intensity map: 0 (core)=100%, 1 (ring 1)=66%, 2 (ring 2)=33%
        intensity_map = np.array([1.0, 0.66, 0.33], dtype=np.float32)
        weights = intensity_map[dist][..., np.newaxis] # Reshape to (58, 58, 1)

        # Apply weights to RGB channels only
        padded_fg[..., :3] *= weights

        # 5. Create the solid black 64x64 canvas
        canvas = np.zeros((64, 64, 4), dtype=np.uint8)
        canvas[..., 3] = 255  # Solid opaque alpha background
        canvas[1:59, 3:61] = padded_fg.astype(np.uint8)

        return canvas


    def render_record(self, cover: np.ndarray, angle: float) -> np.ndarray:
        size = 64

        frame = Image.new("RGBA", (size, size), (0, 0, 0, 255))
        art = Image.fromarray(cover, 'RGBA')

        margin = max(2, size // 32)
        disc_size = size - margin * 2

        # The album cover is the record surface: rotate it first, then cut it into a circular disk.
        art_square = ImageOps.fit(art, (disc_size, disc_size), method=Image.Resampling.LANCZOS)
        rotated = art_square.rotate(angle, resample=Image.Resampling.BICUBIC)

        disc_mask = Image.new("L", (disc_size, disc_size), 0)
        mask_draw = ImageDraw.Draw(disc_mask)
        mask_draw.ellipse((0, 0, disc_size - 1, disc_size - 1), fill=255)
        frame.paste(rotated.convert("RGBA"), (margin, margin), disc_mask)

        draw = ImageDraw.Draw(frame, "RGBA")
        outer = (margin, margin, size - margin - 1, size - margin - 1)
        draw.ellipse(outer, outline=(6, 6, 6, 255), width=max(1, size // 32))

        center = size // 2
        label_radius = max(5, size // 11)
        hole_radius = max(2, size // 25)
        draw.ellipse(
            (
                center - label_radius,
                center - label_radius,
                center + label_radius,
                center + label_radius,
            ),
            fill=(16, 16, 16, 210),
            outline=(180, 180, 180, 90),
        )
        draw.ellipse(
            (
                center - hole_radius,
                center - hole_radius,
                center + hole_radius,
                center + hole_radius,
            ),
            fill=(0, 0, 0, 255),
        )
        return np.array(frame, dtype=np.uint8)


    def render_record_scaled(self, cover: np.ndarray, angle: float) -> np.ndarray:
        size = 64
        frame = Image.new("RGBA", (size, size), (0, 0, 0, 255))
        art = Image.fromarray(cover, 'RGBA')

        # 1. Increased disc size by 1 pixel
        disc_size = 57
        
        # 2. Centered horizontally (64 - 57) / 2 = 3.5. 
        # y_pos = 1 leaves exactly 1 pixel of space at the top border (row 0 is empty).
        x_pos = 3.5
        y_pos = 1

        # The album cover is the record surface: rotate it first, then cut it into a circular disk.
        art_square = ImageOps.fit(art, (disc_size, disc_size), method=Image.Resampling.LANCZOS)
        rotated = art_square.rotate(angle, resample=Image.Resampling.BICUBIC)

        disc_mask = Image.new("L", (disc_size, disc_size), 0)
        mask_draw = ImageDraw.Draw(disc_mask)
        mask_draw.ellipse((0, 0, disc_size - 1, disc_size - 1), fill=255)
        
        # Paste the disc at the new position (Pillow automatically drops float positions down to integers)
        frame.paste(rotated.convert("RGBA"), (int(x_pos), int(y_pos)), disc_mask)

        draw = ImageDraw.Draw(frame, "RGBA")
        
        # 3. Adjusted the outer record rim to match the new size boundaries
        outer = (x_pos, y_pos, x_pos + disc_size - 1, y_pos + disc_size - 1)
        draw.ellipse(outer, outline=(6, 6, 6, 255), width=max(1, size // 32))

        # 4. New geometric center calculation for the center components:
        # center = pos + (size - 1) / 2
        center_x = x_pos + (disc_size - 1) / 2  # 3.5 + 28 = 31.5
        center_y = y_pos + (disc_size - 1) / 2  # 1.0 + 28 = 29.0
        
        label_radius = max(5, size // 11)
        hole_radius = max(2, size // 25)
        
        # Draw vinyl center label aligned to the new true center
        draw.ellipse(
            (
                center_x - label_radius,
                center_y - label_radius,
                center_x + label_radius,
                center_y + label_radius,
            ),
            fill=(16, 16, 16, 210),
            outline=(180, 180, 180, 90),
        )
        
        # Draw spindle hole aligned to the new true center
        draw.ellipse(
            (
                center_x - hole_radius,
                center_y - hole_radius,
                center_x + hole_radius,
                center_y + hole_radius,
            ),
            fill=(0, 0, 0, 255),
        )

        return np.array(frame, dtype=np.uint8)

    
    def add_time_bar(self, cover: np.ndarray) -> np.ndarray:
        if self.current_playback_info.duration is None or self.current_playback_info.progress is None:
            return cover
        
        # dont use aprox value because not valid
        #if self.current_playback_info.progress != self.last_playback_info.progress or self.current_playback_info.is_playing == False:
        #    self.playback_time_aprox = self.current_playback_info.progress

        ratio = self.playback_time_aprox / self.current_playback_info.duration
        ratio = max(0.0, min(1.0, ratio))

        img = Image.fromarray(cover, 'RGBA')
        draw = ImageDraw.Draw(img)

        x0, x1 = 5, 58   
        y = 61           

        # 1. Draw the dynamic total duration track
        draw.line((x0, y, x1, y), fill=self.theme_dark_track)

        # Soft taper the edges using a transparent mix of your dynamic dark track color
        edge_fade_dark = (self.theme_dark_track[0], self.theme_dark_track[1], self.theme_dark_track[2], 120)
        draw.point((x0, y), fill=edge_fade_dark)
        draw.point((x1, y), fill=edge_fade_dark)

        # 2. Draw the dynamic active played progress
        progress_width = int(round(54 * ratio))
        if progress_width > 0:
            tip_x = x0 + progress_width - 1
            
            # Draw the colored progress body
            draw.line((x0, y, tip_x, y), fill=self.theme_progress_track)
            
            # Apply the brightened dynamic glowing playhead tip
            draw.point((tip_x, y), fill=self.theme_playhead_tip)

            # Keep the left side taper matching the color scheme
            edge_fade_body = (self.theme_progress_track[0], self.theme_progress_track[1], self.theme_progress_track[2], 120)
            draw.point((x0, y), fill=edge_fade_body)

        return np.array(img, dtype=np.uint8)

    
    def stop_image_driver(self):
        print("[SPOTIFY IMAGE DRIVER] Stopping Frame Loop ...")
        self.spotify_client.stop_request_thread()
        self.stop_event.set()
        
        #wait for thread if one is active
        try:
            self.frame_thread.join()
        except Exception:
            pass
        
        self.active = False


    def get_current_frame(self)->np.ndarray:
        with self.lock:
            return self.current_frame

    def change_mode(self, new_mode:DisplayMode):

        if new_mode == self.display_mode:
            return
        
        print("[SPOTIFY IMAGE DRIVER] Change mode")
        with self.lock:
            self.change_animation_mode = True
            self.new_display_mode = new_mode


    def update_theme_colors(self, cover_np: np.ndarray):
            """Extracts the dominant color and generates 3 perfectly balanced shades."""
            # 1. Downscale to 1x1 to get the mathematically perfect average color
            pil_img = Image.fromarray(cover_np, 'RGBA')
            one_pixel = pil_img.resize((1, 1), Image.Resampling.LANCZOS)
            dominant_rgb = np.array(one_pixel)[0, 0, :3].astype(np.float32)

            dark_rgb = np.clip(dominant_rgb * 0.15 + 15, 0, 255).astype(np.uint8)
            self.theme_dark_track = (dark_rgb[0], dark_rgb[1], dark_rgb[2], 255)

            # 3. Generate the Active Progress Body
            body_rgb = np.clip(dominant_rgb * 1.1 + 30, 0, 255).astype(np.uint8)
            self.theme_progress_track = (body_rgb[0], body_rgb[1], body_rgb[2], 255)

            # 4. Generate the Playhead Tip
            tip_rgb = np.clip(dominant_rgb * 1.3 + 120, 0, 255).astype(np.uint8)
            self.theme_playhead_tip = (tip_rgb[0], tip_rgb[1], tip_rgb[2], 255)