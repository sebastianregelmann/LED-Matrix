from pathlib import Path
import numpy as np
from PIL import Image
from ImageDriver import ImageDriver
import os 


class StaticImageDriver(ImageDriver):
    image_name : str 
    image_path : Path

    def __init__(self, image_name: str=""):
        #call super constructor
        super().__init__()

        #convert name into path
        self.image_name = image_name
        self.image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IMAGES", image_name)



    def load_image(self):
        try:
            #check if path is valid
            if self.image_path.exists() == False:
                path =  os.path.join(os.path.dirname(os.path.abspath(__file__)), "ErrorImages", "StaticImage", "ImageNotFound.png")
                img = Image.open(path)
                img = np.array(img, dtype=np.uint8)
                img = self.ensure_rgba(img)
                self.current_frame = img
                print(f"[STATIC IMAGE DRIVER] No Image at Path: {self.image_path}")
                return

            #load the image and convert it to np array (64,64,4)
            img = Image.open(self.image_path)
            img = img.convert("RGBA").resize((64,64), Image.Resampling.LANCZOS)
            img = np.array(img, dtype=np.uint8)
            img = self.ensure_rgba(img)
            self.current_frame = img
            print(f"[STATIC IMAGE DRIVER] Loaded Image from: {self.image_path}")
        
        except Exception as e:
            print(f"[STATIC IMAGE DRIVER] Error Loading Image {e}")
            return

    
    def start_image_driver(self):
        print("[STATIC IMAGE DRIVER] Start static image driver")
        #load the image
        self.load_image()
        self.active = True

    def stop_image_driver(self):
        print("[STATIC IMAGE DRIVER] Stop static image driver")
        self.active = False

    def get_current_frame(self)->np.ndarray:
        return self.current_frame

    def change_mode(self, new_image: str):
        self.stop_image_driver()
        self.__init__(new_image)
        self.start_image_driver()