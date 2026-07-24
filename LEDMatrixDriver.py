import numpy as np
import time
from PIL import Image
from ImageLoader import empty_image
from rgbmatrix import RGBMatrix, RGBMatrixOptions

class LEDMatrixDriver():
    brightness: int
    frame: np.ndarray
    active: bool

    # performance debug variables
    last_update = time.perf_counter()
    updates: int = 0

    def __init__(self, brightness: int):   
        self.active = False
        
        # Frame initialized as RGBA (64, 64, 4) to match incoming format
        self.frame = empty_image()
        
        self.brightness = max(0, min(255, brightness))
        self.matrix = None
        self.canvas = None
        
        self.init_led_driver()

    def init_led_driver(self):
        options = RGBMatrixOptions()
        options.rows = 64
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.drop_privileges = False 
        options.hardware_mapping = 'regular'
        
        # Prevent Pi 3 / Zero speed flickering
        options.gpio_slowdown = 1 

        self.matrix = RGBMatrix(options=options)
        self.matrix.brightness = self.brightness
        
        self.canvas = self.matrix.CreateFrameCanvas()
        print("[LED-MATRIX DRIVER] Driver is now Active")

    def update_led_matrix_frame(self):
        if not self.active or self.matrix is None:
            return
            
        # Strip the alpha channel: slice the array to only grab R, G, B channels
        # This creates a (64, 64, 3) view of the array instantly
        rgb_frame = self.frame[..., :3]
        
        # Convert to PIL Image (expected by the C++ binding)
        image = Image.fromarray(rgb_frame, mode='RGB')
        
        # Draw the image to the offline canvas
        self.canvas.SetImage(image)
        
        # Swap the offline canvas with the live display upon the next Vertical Sync
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def update_led_matrix_brightness(self):
        if self.matrix is not None:
            self.matrix.brightness = self.brightness

    def enable_led_matrix(self):
        self.active = True

    def disable_led_matrix(self):
        self.active = False
        if self.matrix is not None:
            self.matrix.Clear()

    def update_brightness(self, brightness: int):
        new_brightness = max(0, min(255, brightness))
        if self.brightness != new_brightness:
            self.brightness = new_brightness
            self.update_led_matrix_brightness()
    
    def update_frame(self, frame: np.ndarray):
        self.frame = frame
        self.update_led_matrix_frame()

        # Debug Performance
        self.updates += 1
        now = time.perf_counter()
        if now - self.last_update >= 1.0:
            print(f"[LED DRIVER] Updates: {self.updates}")
            self.updates = 0
            self.last_update = time.perf_counter()