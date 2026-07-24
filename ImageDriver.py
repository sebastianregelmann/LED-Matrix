import numpy as np
from abc import ABC, abstractmethod
from ImageLoader import empty_image

class ImageDriver(ABC):
    current_frame: np.ndarray

    def __init__(self):
        #initialize frame with empty array
        self.current_frame = empty_image()

    @abstractmethod
    def get_current_frame(self) -> np.ndarray:
        pass


    def ensure_rgba(self, img:np.ndarray) -> np.ndarray:
        # 1. Standardize shape to (H, W, C)
        if img.ndim == 2:
            # Turn (64, 64) into (64, 64, 1)
            img = img[:, :, np.newaxis]
        
        # 2. Get the number of channels (the size of the last dimension)
        channels = img.shape[-1]
        
        # Create our output template (default alpha is 255)
        result =empty_image()
        
        match channels:
            case 1:  # Grayscale
                # Replicate the single channel 3 times for R, G, and B
                rgb = np.repeat(img, 3, axis=-1)
            case 3:  # RGB
                rgb = img
            case 4:  # RGBA
                rgb = img[:, :, :3]
            case _:  # Fallback for unexpected shapes
                rgb = np.zeros((64, 64, 3), dtype=np.uint8)
                
        # Insert the RGB values into our template
        result[:, :, :3] = rgb
        return result
        

    @abstractmethod
    def start_image_driver(self):
        pass


    @abstractmethod
    def stop_image_driver(self):
        pass

    @abstractmethod
    def change_mode(self):
        pass