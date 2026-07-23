from pathlib import Path
import time
import numpy as np
from PIL import Image, ImageSequence
from ImageDriver import ImageDriver
import threading

class GifImageDriver(ImageDriver): 
    frame_thread : threading.Thread
    stop_event : threading.Event
    gif_name : str
    gif_path : Path
    frames :np.ndarray
    frame_index : int
    last_update : float
    duration : float
    lock : object



    def __init__(self, gif_name:str =""):
        #call super constructor
        super().__init__()

        #create a Lock
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        #convert name into path
        self.gif_name = gif_name
        self.gif_path = Path(f"GIFS/{gif_name}")


    def load_gif_frames(self) -> bool: 
        try:
            #check if path is valid
            if self.gif_path.exists() == False:
                img = Image.open("ErrorImages/GIFS/GifNotFound.png")
                img = np.array(img, dtype=np.uint8)
                img = self.ensure_rgba(img)
                with self.lock:
                    self.current_frame = img
                print(f"[GIF IMAGE DRIVER] No GIF at Path: {self.gif_path}")
                return False
        
            #load the gif frames
            gif = Image.open(self.gif_path)
            generated_frames = []
            total_duration_ms = 0

            #loop over the frames
            for frame in ImageSequence.Iterator(gif):
                #get frame time
                frametime = frame.info.get('duration', 100)
                if frametime == 0:
                    frametime = 100
                total_duration_ms += frametime
                
                # 2. Resize the frame using LANCZOS for high-quality downsampling
                frame = frame.convert("RGBA").resize((64,64), Image.Resampling.LANCZOS)
                
                # 3. Convert to NumPy array
                img = np.array(frame, dtype=np.uint8)
                img = self.ensure_rgba(img)
                generated_frames.append(img)
        
            #store frames
            self.frames = np.array(generated_frames)
            with self.lock:
                self.current_frame = self.frames[0]

            #store loop duration
            if self.frames.shape[0] > 1: 
                self.duration = total_duration_ms / 1000.0
            else:
                self.duration = 10.0

            print(f"[GIF IMAGE DRIVER] Create Animation from {self.gif_path}")
            return True
        
        except Exception as e:
            print(f"[GIF IMAGE DRIVER] Error loading gif: {e}")
            with self.lock:
                self.current_frame = np.zeros((64,4,4), dtype=np.uint8)
                self.current_frame[...,3] = 255
            return False


    def update_frame_loop(self):  
        print("[GIF IMAGE DRIVER] Started the gif image driver")     
        try:
            frame_count = self.frames.shape[0]
            frame_interval = self.duration / frame_count
            while not self.stop_event.is_set():    
                # free up cpu time 
                time.sleep(frame_interval / 2)

                #if time is up display next frame
                now = time.perf_counter()
                if (now - self.last_update) >= frame_interval:
                    with self.lock:
                        self.frame_index = (self.frame_index + 1) % frame_count
                        self.current_frame = self.frames[self.frame_index]
                    self.last_update = time.perf_counter()
        except Exception as e:
            print(f"[GIF IMAGE DRIVER] Error in frame thread: {e}")
            with self.lock:
                self.current_frame = np.zeros((64,4,4), dtype=np.uint8)
                self.current_frame[...,3] = 255               
        print("[GIF IMAGE DRIVER] Stopped Frame Loop")


    def stop_image_driver(self):
        print("[GIF IMAGE DRIVER] Stopping Frame Loop ...")
        self.stop_event.set()
        
        #wait for thread if one is active
        try:
            self.frame_thread.join()
        except Exception:
            pass

        self.active = False
        

    def start_image_driver(self):
        print("[GIF IMAGE DRIVER] Starting the gif image driver")
        
        #load the gif
        if self.load_gif_frames() == False:
            self.active = True
            return

        #set initial variables
        self.last_update = time.perf_counter()
        self.frame_index = 0

        #Start the thread
        self.stop_event.clear()
        self.frame_thread = threading.Thread(target=self.update_frame_loop)

        #start own thread for updating frames
        self.active = True
        self.frame_thread.start()



    def get_current_frame(self)->np.ndarray:
        with self.lock:
            return self.current_frame
        

    def change_mode(self, new_gif:str):
        self.stop_image_driver()
        super().__init__()
        
        #convert name into path
        self.gif_name = new_gif
        self.gif_path = Path(f"GIFS/{new_gif}")

        self.start_image_driver()

