import numpy as np
from ImageDriver import ImageDriver
import threading
from Animator import AnimationMode, AnimationSettings, Animator, Rain, Fire, Plasma, LavaLamp, DriftingFog, Starfield, SlowClock
import time
from ImageLoader import load_animator_missing, empty_image

class AnimationImageDriver(ImageDriver):
    animation_mode : AnimationMode
    animation_settings : AnimationSettings
    animator : Animator

    frame_thread : threading.Thread
    stop_event : threading.Event
    lock : object
    last_update : float



    def __init__(self, animation_mode: AnimationMode, animation_settings:AnimationSettings):
        #call super constructor
        super().__init__()

        self.animation_mode = animation_mode
        self.animation_settings = animation_settings
        self.animator = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        print(f"[ANIMATION IMAGE DRIVER] Animator ready to start")

    def load_animator(self):
        try:
            with self.lock:
                match self.animation_mode:
                    case AnimationMode.NONE:
                        img = load_animator_missing()
                        self.current_frame = img
                        self.animator = None
                        print(f"[ANIMATION IMAGE DRIVER] Animator not found")
                        return

                    case AnimationMode.RAIN:
                        self.animator = Rain(self.animation_settings)
                    case AnimationMode.FIRE:
                        self.animator = Fire(self.animation_settings)
                    case AnimationMode.PLASMA:
                        self.animator = Plasma(self.animation_settings)
                    case AnimationMode.LAVALAMP:
                        self.animator = LavaLamp(self.animation_settings)
                    case AnimationMode.DRIFTING_FOG:
                        self.animator = DriftingFog(self.animation_settings)
                    case AnimationMode.STARFIELD:
                        self.animator = Starfield(self.animation_settings)
                    case AnimationMode.CLOCK:
                        self.animator = SlowClock(self.animation_settings)
                print(f"[ANIMATION IMAGE DRIVER] Loaded Animator: {self.animation_mode}")
            
        except Exception as e:
            print(f"[ANIMATION IMAGE DRIVER] Error Loading Animator {e}")
            with self.lock:
                self.animator = None
            return

    def update_frame_loop(self):  
        print("[ANIMATION IMAGE DRIVER] Started the animation image driver")     
        frame_interval = 1.0 / 60

        try:
            while not self.stop_event.is_set():    
                # free up cpu time 
                time.sleep(frame_interval / 2)

                #if time is up display next frame
                now = time.perf_counter()
                if (now - self.last_update) >= frame_interval:
                    with self.lock:
                        self.current_frame = self.animator.get_next_frame()
                    self.last_update = time.perf_counter()
        except Exception as e:
            print(f"[ANIMATION IMAGE DRIVER] Error in update Thread {e}")
            with self.lock:
                self.current_frame = empty_image()
        print("[ANIMATION IMAGE DRIVER] Stopped Frame Loop")



    def start_image_driver(self):
        print("[ANIMATION IMAGE DRIVER] Starting Animation image driver")
        
        #load the animator
        self.load_animator()

        if self.animator is None:
            return
        
        #set initial variables
        self.last_update = time.perf_counter()
        
        #Start the thread
        self.stop_event.clear()
        self.frame_thread = threading.Thread(target=self.update_frame_loop)
        self.frame_thread.start()

    def stop_image_driver(self):
        print("[ANIMATION IMAGE DRIVER] Stopping Frame Loop ...")
        self.stop_event.set()
        #wait for finished thread
        try:
            self.frame_thread.join()
        except Exception:
            pass


    def get_current_frame(self)->np.ndarray:
        with self.lock:
             return self.current_frame
        

    
    def change_mode(self, animation_mode: AnimationMode, animation_settings:AnimationSettings):
        #check if animation mode is different
        if self.animation_mode != animation_mode:
            print("[ANIMATION IMAGE DRIVER] Change animation mode")
            self.stop_image_driver()
            
            # Manually update the state instead of calling __init__
            self.animation_mode = animation_mode
            self.animation_settings = animation_settings
            self.animator = None 
            
            self.start_image_driver()
            return
        
        if self.animation_settings.values_changed(animation_settings):
            #check if animator exists
            if self.animator is not None:
                with self.lock:
                    print("[ANIMATION IMAGE DRIVER] Change animation settings")
                    self.animation_settings = animation_settings
                    self.animator.change_animation_settings(self.animation_settings)



        
        
        
