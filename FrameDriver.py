from ImageDriver import ImageDriver
from StaticImageDrive import StaticImageDriver
from GifImageDriver import GifImageDriver
from AnimationImageDriver import AnimationImageDriver, AnimationMode, AnimationSettings
from SpotifyImageDriver import SpotifyImageDriver, DisplayMode
import json
import time
import threading
from LEDMatrixDriver import LEDMatrixDriver
import os
from ImageLoader import get_abs_path, path_exists

class FrameDriver():
    current_image_driver: ImageDriver = None
    static_image_driver: StaticImageDriver = None
    gif_image_driver: GifImageDriver = None
    animation_image_driver: AnimationImageDriver = None
    spotify_image_driver: SpotifyImageDriver = None

    lock: threading.Lock
    change_mode: bool = False
    new_mode: dict = None

    led_driver: LEDMatrixDriver

    save_status_to_cache: bool

    def __init__(self, save_status_to_cache:bool = False):
        self.lock = threading.Lock()
        self.save_status_to_cache = save_status_to_cache

        # load the last cached settings
        if self.save_status_to_cache:
            if not self.load_cached_settings():
                self.initialize_default()
        else:
            self.initialize_default()
        print("[FRAME DRIVER] Frame driver is Ready")
        self.save_status_cache()

        thread = threading.Thread(target=self.update_loop, daemon=True)
        thread.start()

    def update_loop(self):
        update_rate = 1 / 90  # ~0.01333 seconds (13.3ms)
        last_update = time.perf_counter()

        print("[FRAME DRIVER] Starting Matrix Update Loop Now")
        while True:
            try:
                # 1. Check if mode changed
                mode_to_apply = None
                with self.lock:
                    if self.change_mode:
                        mode_to_apply = self.new_mode
                        self.change_mode = False

                if mode_to_apply is not None:
                    self.change_mode_after_request(mode_to_apply)

                # 2. Check timing for render
                now = time.perf_counter()
                timediff = now - last_update

                if timediff >= update_rate:
                    last_update = now

                    if self.current_image_driver is None:
                        self.led_driver.disable_led_matrix()
                        time.sleep(update_rate)
                        continue

                    # Fetch driver reference under lock, safely
                    with self.lock:
                        # 3. Render frame OUTSIDE the lock so external API requests aren't starved
                        frame = self.current_image_driver.get_current_frame()
                    self.led_driver.update_frame(frame)

                # Sleep to allow context switches for external API calls
                time.sleep(0.001)

            except Exception as e:
                print(f"[FRAME DRIVER] Error in Frame Loop: {e}")
                time.sleep(update_rate)
                last_update = time.perf_counter()

    def initialize_default(self):
        self.led_driver = LEDMatrixDriver(127)
        self.static_image_driver = StaticImageDriver("Test.png")
        self.gif_image_driver = GifImageDriver("Test.gif")
        self.animation_image_driver = AnimationImageDriver(
            AnimationMode.NONE, AnimationSettings(False, 255, 0, 0, 0.5, 0.001)
        )
        self.spotify_image_driver = SpotifyImageDriver(2, DisplayMode.DISC)
        print("[FRAME DRIVER] Initialied with default Settings")

    def load_cached_settings(self) -> bool:
        if path_exists(os.path.join("StatusCache", "Status.json")) == False:
            print(f"[FRAME DRIVER] Path does not exist: {get_abs_path(os.path.join("StatusCache", "Status.json"))}")
            return False
        
        path = get_abs_path(os.path.join("StatusCache", "Status.json"))
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)

            brightness = data.get("Brightness", 127)
            self.led_driver = LEDMatrixDriver(brightness)

            image_mode_image = data.get("ImageMode", {}).get("Image", "LastImageName.png")
            self.static_image_driver = StaticImageDriver(image_mode_image)

            gif_mode_gif = data.get("GifMode", {}).get("Gif", "LastGifName.gif")
            self.gif_image_driver = GifImageDriver(gif_mode_gif)

            anim_data = data.get("AnimationMode", {})
            anim_settings_data = anim_data.get("AnimationSettings", {})
            animation_mode = self.decode_animation_mode(anim_data.get("Mode", "NONE"))
            
            animation_settings = AnimationSettings(
                anim_settings_data.get("ColorFade", False),
                anim_settings_data.get("Red", 255),
                anim_settings_data.get("Green", 0),
                anim_settings_data.get("Blue", 0),
                anim_settings_data.get("AnimationSpeed", 0.5),
                anim_settings_data.get("ColorFadeSpeed", 0.001)
            )
            self.animation_image_driver = AnimationImageDriver(animation_mode, animation_settings)

            spotify_mode = self.decode_spotify_mode(data.get("SpotifyMode", {}).get("Mode", "DISC"))
            self.spotify_image_driver = SpotifyImageDriver(2, spotify_mode)

            print(f"[FRAME DRIVER] Loaded Status from: {path}")
            return True

    def decode_animation_mode(self, mode: str) -> AnimationMode:
        match mode:
            case "RAIN": return AnimationMode.RAIN
            case "FIRE": return AnimationMode.FIRE
            case "PLASMA": return AnimationMode.PLASMA
            case "LAVALAMP": return AnimationMode.LAVALAMP
            case "DRIFTING_FOG": return AnimationMode.DRIFITNG_FOG
            case "STARFIELD": return AnimationMode.STARFIELD
            case "CLOCK": return AnimationMode.CLOCK
            case _: return AnimationMode.NONE

    def decode_spotify_mode(self, mode: str) -> DisplayMode:
        match mode:
            case "COVER": return DisplayMode.COVER
            case "DISC_TIME": return DisplayMode.DISC_TIME
            case "COVER_TIME": return DisplayMode.COVER_TIME
            case _: return DisplayMode.DISC

    def handle_mode_change_request(self, request: dict):
        with self.lock:
            self.new_mode = request
            self.change_mode = True
        print("[FRAME DRIVER] Received Mode Change Request")

    def stop_current_image_driver(self):
        if self.current_image_driver is not None:
            self.current_image_driver.stop_image_driver()
            self.current_image_driver = None

    def change_mode_after_request(self, new_mode: dict):
        # Lock during driver reconfiguration to prevent race conditions
        print("[FRAME DRIVER] Handling Mode Change Request now ...")
        with self.lock:
            data = new_mode

            enabled = data.get("Enabled", False)
            brightness = data.get("Brightness", 127)
            self.change_led_matrix_settings(enabled, brightness)

            if not enabled:
                self._save_status_cache_unlocked()
                return

            image_enabled = data.get("ImageMode", {}).get("Enabled", False)
            image_path = data.get("ImageMode", {}).get("Image", "LastImageName.png")
            self.change_image_mode(image_enabled, image_path)

            gif_enabled = data.get("GifMode", {}).get("Enabled", False)
            gif_name = data.get("GifMode", {}).get("Gif", "LastGifName.gif")
            self.change_gif_mode(gif_enabled, gif_name)

            anim_data = data.get("AnimationMode", {})
            anim_settings_data = anim_data.get("AnimationSettings", {})
            animation_enabled = anim_data.get("Enabled", False)
            animation_mode = self.decode_animation_mode(anim_data.get("Mode", "NONE"))
            
            animation_settings = AnimationSettings(
                anim_settings_data.get("ColorFade", False),
                anim_settings_data.get("Red", 255),
                anim_settings_data.get("Green", 0),
                anim_settings_data.get("Blue", 0),
                anim_settings_data.get("AnimationSpeed", 0.5),
                anim_settings_data.get("ColorFadeSpeed", 0.001)
            )
            self.change_animaiton_mode(animation_enabled, animation_mode, animation_settings)

            spotify_enabled = data.get("SpotifyMode", {}).get("Enabled", False)
            spotify_mode = self.decode_spotify_mode(data.get("SpotifyMode", {}).get("Mode", "DISC"))
            self.change_spotify_mode(spotify_enabled, spotify_mode)

            print("[FRAME DRIVER] Handled Mode Change Request")
            self._save_status_cache_unlocked()

    def change_led_matrix_settings(self, enabled: bool, brightness: int):
        if not enabled:
            self.stop_current_image_driver()
            self.led_driver.disable_led_matrix()
        else:
            self.led_driver.enable_led_matrix()

        self.led_driver.update_brightness(brightness)

    def change_image_mode(self, enabled: bool, image: str):
        if not isinstance(self.current_image_driver, StaticImageDriver) and not enabled:
            return

        if not isinstance(self.current_image_driver, StaticImageDriver) and enabled:
            self.stop_current_image_driver()
            self.static_image_driver = StaticImageDriver(image)
            self.current_image_driver = self.static_image_driver
            self.current_image_driver.start_image_driver()
            return

        if isinstance(self.current_image_driver, StaticImageDriver) and not enabled:
            self.stop_current_image_driver()
            return

        if isinstance(self.current_image_driver, StaticImageDriver) and enabled:
            if self.static_image_driver.image_name != image:
                self.static_image_driver.change_mode(image)

    def change_gif_mode(self, enabled: bool, gif: str):
        if not isinstance(self.current_image_driver, GifImageDriver) and not enabled:
            return

        if not isinstance(self.current_image_driver, GifImageDriver) and enabled:
            self.stop_current_image_driver()
            self.gif_image_driver = GifImageDriver(gif)
            self.current_image_driver = self.gif_image_driver
            self.current_image_driver.start_image_driver()
            return

        if isinstance(self.current_image_driver, GifImageDriver) and not enabled:
            self.stop_current_image_driver()
            return

        if isinstance(self.current_image_driver, GifImageDriver) and enabled:
            if self.gif_image_driver.gif_name != gif:
                self.gif_image_driver.change_mode(gif)

    def change_animaiton_mode(self, enabled: bool, animation_mode: AnimationMode, animation_settings: AnimationSettings):
        if not isinstance(self.current_image_driver, AnimationImageDriver) and not enabled:
            return

        if not isinstance(self.current_image_driver, AnimationImageDriver) and enabled:
            self.stop_current_image_driver()
            self.animation_image_driver = AnimationImageDriver(animation_mode, animation_settings)
            self.current_image_driver = self.animation_image_driver
            self.current_image_driver.start_image_driver()
            return

        if isinstance(self.current_image_driver, AnimationImageDriver) and not enabled:
            self.stop_current_image_driver()
            return

        if isinstance(self.current_image_driver, AnimationImageDriver) and enabled:
            if self.animation_image_driver.animation_mode != animation_mode or self.animation_image_driver.animation_settings != animation_settings:
                self.animation_image_driver.change_mode(animation_mode, animation_settings)

    def change_spotify_mode(self, enabled: bool, display_mode: DisplayMode):
        if not isinstance(self.current_image_driver, SpotifyImageDriver) and not enabled:
            return

        if not isinstance(self.current_image_driver, SpotifyImageDriver) and enabled:
            self.stop_current_image_driver()
            self.spotify_image_driver = SpotifyImageDriver(2, display_mode)
            self.current_image_driver = self.spotify_image_driver
            self.current_image_driver.start_image_driver()
            return

        if isinstance(self.current_image_driver, SpotifyImageDriver) and not enabled:
            self.stop_current_image_driver()
            return

        if isinstance(self.current_image_driver, SpotifyImageDriver) and enabled:
            if self.spotify_image_driver.display_mode != display_mode:
                self.spotify_image_driver.change_mode(display_mode)

    def _build_status_dict(self) -> dict:
        """Internal helper to safely construct status dict without holding lock."""
        return {
            "Enabled": self.led_driver.active if self.led_driver else False,
            "Brightness": self.led_driver.brightness if self.led_driver else 127,
            "ImageMode": {
                "Enabled": isinstance(self.current_image_driver, StaticImageDriver),
                "Image": self.static_image_driver.image_name if self.static_image_driver else ""
            },
            "GifMode": {
                "Enabled": isinstance(self.current_image_driver, GifImageDriver),
                "Gif": self.gif_image_driver.gif_name if self.gif_image_driver else ""
            },
            "AnimationMode": {
                "Enabled": isinstance(self.current_image_driver, AnimationImageDriver),
                "Mode": self.animation_image_driver.animation_mode.name if self.animation_image_driver else "NONE",
                "AnimationSettings": {
                    "ColorFade": self.animation_image_driver.animation_settings.color_fade,
                    "Red": self.animation_image_driver.animation_settings.red,
                    "Green": self.animation_image_driver.animation_settings.green,
                    "Blue": self.animation_image_driver.animation_settings.blue,
                    "AnimationSpeed": self.animation_image_driver.animation_settings.animation_speed,
                    "ColorFadeSpeed": self.animation_image_driver.animation_settings.color_fade_speed
                } if self.animation_image_driver else {}
            },
            "SpotifyMode": {
                "Enabled": isinstance(self.current_image_driver, SpotifyImageDriver),
                "Mode": self.spotify_image_driver.display_mode.name if self.spotify_image_driver else "DISC"
            }
        }

    def current_status(self) -> dict:
        """Thread-safe status endpoint call."""
        with self.lock:
            return self._build_status_dict()

    def _save_status_cache_unlocked(self):
        #Exit if Saving Status is not wanted
        if self.save_status_to_cache == False:
            return
        
        try: 
            """Helper to write cache when lock is already acquired."""

            folder = get_abs_path("StatusCache")
            # Use makedirs instead of mkdir to safely support exist_ok=True
            os.makedirs(folder, exist_ok=True)
            file_path = get_abs_path(os.path.join("StatusCache", "Status.json"))

            status_data = self._build_status_dict()

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=4)

            print(f"[FRAME DRIVER] Saved Status to: {file_path}")
        except Exception as e:
            print(f"[FRAME DRIVER] Could not save token cache to: {get_abs_path(os.path.join("StatusCache", "Status.json"))} Error: {e}")

    def save_status_cache(self):
        """Public method for cache saving."""
        with self.lock:
            self._save_status_cache_unlocked()