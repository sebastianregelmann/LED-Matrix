import numpy as np
from PIL import Image
from ImageDriver import ImageDriver
from ImageLoader import load_image_missing, get_image_abs_path, image_path_exists, empty_image

class StaticImageDriver(ImageDriver):
    image_name : str 

    def __init__(self, image_name: str=""):
        #call super constructor
        super().__init__()

        #Save the name
        self.image_name = image_name
        print("[STATIC IMAGE DRIVER] Static image driver Ready")



    def load_image(self):
        try:
            #check if path is valid
            if image_path_exists(self.image_name) == False:
                img = load_image_missing()
                img = self.ensure_rgba(img)
                self.current_frame = img
                print(f"[STATIC IMAGE DRIVER] No Image at Path: {get_image_abs_path(self.image_name)}")
                return

            #load the image and convert it to np array (64,64,4)
            path = get_image_abs_path(self.image_name)
            img = Image.open(path)
            img = img.convert("RGBA").resize((64,64), Image.Resampling.LANCZOS)
            img = np.array(img, dtype=np.uint8)
            img = self.ensure_rgba(img)
            self.current_frame = img
            print(f"[STATIC IMAGE DRIVER] Loaded Image from: {get_image_abs_path(self.image_name)}")
        
        except Exception as e:
            self.current_frame = empty_image()
            print(f"[STATIC IMAGE DRIVER] Error Loading Image {e}")
            return

    
    def start_image_driver(self):
        print("[STATIC IMAGE DRIVER] Start static image driver")
        #load the image
        self.load_image()

    def stop_image_driver(self):
        print("[STATIC IMAGE DRIVER] Stop static image driver")

    def get_current_frame(self)->np.ndarray:
        return self.current_frame

    def change_mode(self, new_image: str):
        self.stop_image_driver()
        self.__init__(new_image)
        self.start_image_driver()