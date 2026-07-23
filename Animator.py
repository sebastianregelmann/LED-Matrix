from abc import ABC, abstractmethod
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import random
import cv2
from enum import Enum

class AnimationMode(Enum):
    NONE = 1,
    RAIN = 2
    FIRE = 3
    PLASMA =4
    LAVALAMP = 5
    DRIFITNG_FOG = 6
    STARFIELD = 7
    CLOCK = 8


@dataclass
class AnimationSettings:
    # Fields and their defaults
    color_fade: bool = False
    red: int = 0
    green: int = 0
    blue: int = 0
    animation_speed: float = 0.5
    color_fade_speed: float = 0.001
    
    def values_changed(self, new_settings: "AnimationSettings") -> bool:
        """Returns True if any setting differs from the new settings."""
        # Dataclasses automatically generate an __ne__ (not equal) operator 
        # that checks every property systematically.
        return self != new_settings


# 1. Define the Abstract Base Class
class Animator(ABC):

    frame: np.ndarray
    animation_settings :AnimationSettings
    hue : float
    saturation : float

    def __init__(self, animation_settings: AnimationSettings):
        self.animation_settings = animation_settings
        self.hue = 0
        self.saturation = 0.5
        self.frame = np.zeros((64,64,4), dtype=np.uint8)
        self.frame[...,3] = 255

    def change_animation_settings(self, animation_settings : AnimationSettings):
        self.animation_settings = animation_settings


    @abstractmethod
    def get_next_frame(self) -> np.ndarray:
        """Must be implemented by subclasses"""
        # update the animation
        return self.frame
    
    def color_mask(self, mask:np.ndarray):
        #update color based on settings
        if self.animation_settings.color_fade:
            self.hue = (self.hue + self.animation_settings.color_fade_speed) % 1.0
            color = self.get_rgb_from_hsv(self.hue, self.saturation)
        else: 
            color = (self.animation_settings.red, self.animation_settings.green, self.animation_settings.blue)

        #apply the color to the mask
        self.frame = self.apply_color(mask=mask, color=color)
        #self.frame[..., 3] = 255
    
    def apply_color(self, mask:np.ndarray, color: tuple) -> np.ndarray:
        #create color
        color_values = np.array([color[0], color[1], color[2], 255], dtype=np.uint8) 
        #get intensity
        intensity = mask[:, :, :].astype(np.float32) / 255.0
        #apply color
        result = color_values * intensity
        #Set alpha to 255
        result[:, :, 3] = 255
        
        return result.astype(dtype=np.uint8)
    
    def get_rgb_from_hsv(self, hue:float, saturation:float) -> tuple:
        hsv_scaled = np.array([[[hue * 179, saturation * 255, 180]]], dtype=np.uint8)
        # Convert to RGB (OpenCV uses BGR by default, so we use COLOR_HSV2RGB)
        rgb = cv2.cvtColor(hsv_scaled, cv2.COLOR_HSV2RGB)
        return tuple(rgb[0][0])

    @staticmethod
    def smoothstep(edge0, edge1, x):
        t = np.clip((x - edge0) / (edge1 - edge0), 0, 1)
        return t * t * (3 - 2 * t)



class Rain(Animator):
    def __init__(self, animation_settings : AnimationSettings):
        #call base constructor
        super().__init__(animation_settings)

        self.drops = []
        for _ in range(50):
            self.drops.append(
                [
                    np.random.randint(0, 64),
                    np.random.randint(0, 64),
                    np.random.uniform(1.0, 3.0),  # speed
                    np.random.randint(150, 255),  # alpha/brightness
                ]
            ) 

        self.mask = np.zeros((64,64,4), dtype=np.uint8)


    def get_next_frame(self) -> np.ndarray:
        # 1. Create Trails
        self.mask = (self.mask * 0.8).astype(np.uint8)

        # 2. Update and draw drops
        for drop in self.drops:
            x, y, speed, alpha = drop

            # Draw the drop (white rain)
            ix, iy = int(x), int(y)
            if 0 <= ix < 64 and 0 <= iy < 64:
                self.mask[iy, ix] = [255, 255, 255, alpha]

            # Update position
            drop[1] += speed * self.animation_settings.animation_speed

            # Reset drop if it hits the bottom
            if drop[1] >= 64:
                drop[1] = 0
                drop[0] = np.random.randint(0, 64)

        self.color_mask(self.mask)
        return self.frame

class Fire(Animator):
    def __init__(self, animation_settings: AnimationSettings):
        super().__init__(animation_settings)
        
        self.width = self.frame.shape[1]
        self.height = self.frame.shape[0]
        
        # Create an extended internal buffer height to handle fuel off-screen
        self.buffer_padding = 4
        self.buffer_height = self.height + self.buffer_padding
        self.fire_buffer = np.zeros((self.buffer_height, self.width), dtype=np.float32)
        
        # Fixed number of big flames locked securely at exactly 3
        self.big_flame_x = random.sample(range(12, self.width - 12), 3)
        
        # Persistent buffer to keep small bottom flames moving fluidly
        self.small_flames_fuel = np.zeros(self.width, dtype=np.float32)
        
        # Particle system for sparks
        self.sparks = []
        
        # Speed control accumulator
        self.update_accumulator = 0.0

    def get_next_frame(self) -> np.ndarray:
        # ---------------------------------------------------------
        # 1. SPEED CONTROL
        # ---------------------------------------------------------
        self.update_accumulator += self.animation_settings.animation_speed
        steps = int(self.update_accumulator)
        self.update_accumulator -= steps
        
        # Run simulation mechanics based on speed steps
        for _ in range(steps):
            
            # --- A. RE-FUEL THE BASE (Injected Off-Screen) ---
            # Generate smooth macro-structures for small flames using low-res noise
            low_res_noise = np.random.uniform(110, 170, self.width // 4)
            smooth_noise = cv2.resize(
                low_res_noise[np.newaxis, :], 
                (self.width, 1), 
                interpolation=cv2.INTER_LINEAR
            )[0]
            
            # Smooth interpolation over time avoids any high-frequency flickering chaos
            self.small_flames_fuel = (self.small_flames_fuel * 0.88) + (smooth_noise * 0.12)
            
            # Write the smooth fuel entirely into the hidden bottom padding rows
            self.fire_buffer[self.height:, :] = self.small_flames_fuel
            
            # Inject the 3 fixed big flames cleanly into the hidden rows below the screen
            for x in self.big_flame_x:
                wobble = random.randint(-1, 1)
                cx = np.clip(x + wobble, 0, self.width - 1)
                self.fire_buffer[self.height:, max(0, cx-3):min(self.width, cx+4)] = 230

            # --- B. PROPAGATION & SMOOTHING (Applied across entire buffer) ---
            # Shift rows to pull heat upward
            shift1 = np.roll(self.fire_buffer, -1, axis=0)          
            shift1_l = np.roll(shift1, 1, axis=1)                   
            shift1_r = np.roll(shift1, -1, axis=1)                  
            shift2 = np.roll(self.fire_buffer, -2, axis=0)          
            
            # This averaging now naturally blends the fuel up into the first visible row
            self.fire_buffer = (shift1 + shift1_l + shift1_r + shift2) * 0.246
            
            # Cool down to create structural smoke pockets uniformly
            cooling_map = np.random.uniform(0, 3.5, (self.buffer_height, self.width))
            self.fire_buffer -= cooling_map
            self.fire_buffer = np.clip(self.fire_buffer, 0, 255)

            # --- C. SPARK PARTICLES ---
            if random.random() < 0.25:  
                self.sparks.append({
                    'x': random.choice(self.big_flame_x) + random.uniform(-2, 2),
                    'y': float(self.height - 1),
                    'vx': random.uniform(-0.3, 0.3),
                    'vy': random.uniform(-1.2, -2.5),
                    'life': random.uniform(12, 28)
                })
                
            active_sparks = []
            for spark in self.sparks:
                spark['x'] += spark['vx']
                spark['y'] += spark['vy']
                spark['life'] -= 1
                
                if spark['life'] > 0 and 0 <= int(spark['x']) < self.width and 0 <= int(spark['y']) < self.height:
                    px, py = int(spark['x']), int(spark['y'])
                    self.fire_buffer[py, px] = min(255, self.fire_buffer[py, px] + 140)
                    active_sparks.append(spark)
                    
            self.sparks = active_sparks

        # ---------------------------------------------------------
        # 2. SMOOTH SHADING AND RGB RENDERING
        # ---------------------------------------------------------
        # Extract only the visible portion of the heat buffer for rendering
        visible_fire_map = self.fire_buffer[:self.height, :]
        
        mask = np.expand_dims(visible_fire_map, axis=-1).astype(np.uint8)
        
        # Generate base color matrix using parent rules
        self.color_mask(mask)
        
        # Soft continuous thermal lighting calculation
        heat_normalized = (visible_fire_map / 255.0)
        
        boost_r = (heat_normalized ** 2.2) * 70
        boost_g = (heat_normalized ** 2.5) * 60
        boost_b = (heat_normalized ** 3.0) * 40 
        
        # Output clean, reliable, and uniformly smooth RGB channels
        self.frame[..., 0] = np.clip(self.frame[..., 0] + boost_r, 0, 255).astype(np.uint8)
        self.frame[..., 1] = np.clip(self.frame[..., 1] + boost_g, 0, 255).astype(np.uint8)
        self.frame[..., 2] = np.clip(self.frame[..., 2] + boost_b, 0, 255).astype(np.uint8)

        return self.frame

class Plasma(Animator):
    def __init__(self, animation_settings : AnimationSettings):
        #call base constructor
        super().__init__(animation_settings)

        self.blobsize = 9        
        
        # INCREASED FREQUENCY: Multiplying by 8 instead of 4 makes the blobs smaller
        x = np.linspace(0, self.blobsize, 64)
        y = np.linspace(0, self.blobsize, 64)
        self.xv, self.yv = np.meshgrid(x, y)
        self.t = 0

    def get_next_frame(self) -> np.ndarray:
        self.t += random.uniform(0.01,0.03) * self.animation_settings.animation_speed

        # Generate smaller, tighter noise field
        v = (
                np.sin(self.xv + np.sin(self.t * 0.5) * 2) +
                np.sin(self.yv + np.cos(self.t * 0.3) * 5) +
                np.sin((self.xv + self.yv) * 0.5 + self.t * 0.7) +
                np.sin(np.sqrt((self.xv - 32)**2 + (self.yv - 32)**2) * 0.5 - self.t * 0.9) +
                np.cos(np.sqrt((self.xv - 32)**2 + (self.yv - 32)**2) * 0.5 - self.t * 0.9) 
            )

        # Normalize to 0-1
        field = (np.sin(v) + 1) / 2

        #expand in each dimension
        mask = (np.repeat(field[:, :, np.newaxis], 4, axis=2) * 255).astype(dtype=np.uint8)
        self.color_mask(mask)
        return self.frame



class LavaLamp(Animator):
    def __init__(self, animation_settings : AnimationSettings):
        #call base constructor
        super().__init__(animation_settings)
        
        self.num_blobs = 5

        self.centers = np.random.rand(self.num_blobs, 2) * [64, 64]
        self.speeds = (np.random.rand(self.num_blobs, 2) - 0.5) * 0.8

        self.radius = 12.0

        # Each blob has its own fade timing
        self.fade_phase = np.random.rand(self.num_blobs) * 2 * np.pi
        
        # Each blob has a different shade (0.75–1.25)
        self.shades = np.random.uniform(0.75, 1.25, self.num_blobs)
        
        self.size_speed = 0.02
        self.t = 0
        self.y, self.x = np.mgrid[0:64, 0:64]

    def get_next_frame(self):
        self.t += self.size_speed * self.animation_settings.animation_speed

        # Vectorized boundary bounce
        self.centers += self.speeds
        
        # Identify out-of-bounds indices and flip speeds
        mask_out = (self.centers < 0) | (self.centers > [64, 64])
        self.speeds[mask_out] *= -1
        self.centers = np.clip(self.centers, 0, [64, 64])

        # Vectorized density calculation
        # self.centers: (5, 2) -> reshaped to (1, 1, 5, 2) for broadcasting
        # self.x, self.y: (64, 64) -> reshaped to (64, 64, 1)
        dist2 = (self.x[..., None] - self.centers[:, 0])**2 + \
                (self.y[..., None] - self.centers[:, 1])**2
        
        # Calculate fade for all blobs at once
        fades = 0.2 + 0.8 * (np.sin(self.t * 0.2 + self.fade_phase) * 0.5 + 0.5)
        
        # Calculate density (64, 64, 5)
        blobs = np.exp(-dist2 / (2 * self.radius**2)) * fades
        
        # Sum across the blob dimension (axis 2)
        density = blobs.sum(axis=2)
        
        # Apply mask and color
        mask_val = self.smoothstep(0.3, 0.75, density)
        
        # #Combine Masks and fill alpha channel
        mask = (np.repeat(mask_val[..., np.newaxis], 4, axis=2) * 255).astype(dtype=np.uint8)
        mask[..., 3] = 255

        #fill with color
        self.color_mask(mask)
        return self.frame


class DriftingFog(Animator):
    def __init__(self, animation_settings : AnimationSettings):
        #call base constructor
        super().__init__(animation_settings)

        self.num_clouds = 14

        self.y, self.x = np.mgrid[0:64, 0:64]

        # Cloud positions
        self.centers = np.random.rand(self.num_clouds, 2) * [64, 64]

        # Very slow diagonal movement
        self.speeds = np.random.uniform(0.1, 0.4, (self.num_clouds, 2))
        self.speeds[:, 1] *= 0.8

        # Smaller soft clouds
        self.radius = np.random.uniform(8, 25, self.num_clouds)

        # Individual cloud breathing phases
        self.fade_phase = np.random.rand(self.num_clouds) * 2 * np.pi
        self.t = 0


    def get_next_frame(self):
        self.t += 0.02 * self.animation_settings.animation_speed

        clouds_a = np.zeros((64,64))
        clouds_b = np.zeros((64,64))

        for i in range(self.num_clouds):

            # Drift through the scene
            self.centers[i] += self.speeds[i] * self.animation_settings.animation_speed

            # Wrap around edges
            self.centers[i, 0] %= 64
            self.centers[i, 1] %= 64

            cx, cy = self.centers[i]

            # Wrap-aware distance
            dx = np.minimum(np.abs(self.x - cx), 64 - np.abs(self.x - cx))

            dy = np.minimum(np.abs(self.y - cy), 64 - np.abs(self.y - cy))

            dist2 = dx**2 + dy**2

            # Soft Gaussian cloud
            cloud = np.exp(-dist2 / (2 * self.radius[i] ** 2))

            # Gentle breathing effect
            fade = 0.65 + 0.25 * (
                0.5 + 0.5 * np.sin(self.t * 0.25 + self.fade_phase[i])
            )

            cloud *= fade

            # Alternate complementary colors
            if i % 2 == 0:
                clouds_a += cloud * (1/self.num_clouds)
            else:
                clouds_b += cloud* (1/self.num_clouds)

        clouds_a = np.clip(clouds_a, 0, 0.45)
        mask_a = self.smoothstep(0.02, 0.35, clouds_a)

        clouds_b = np.clip(clouds_b, 0, 0.45)
        mask_b = self.smoothstep(0.02, 0.35, clouds_b)

        mask_a = (np.repeat(mask_a[..., np.newaxis], 4, axis=2) * 255).astype(dtype=np.uint8)
        mask_b = (np.repeat(mask_b[..., np.newaxis], 4, axis=2) * 255).astype(dtype=np.uint8)


        if self.animation_settings.color_fade:
            self.hue = (self.hue +self.animation_settings.color_fade_speed) % 1.0
            color_a = self.get_rgb_from_hsv(self.hue, self.saturation)
            color_b = self.get_rgb_from_hsv((self.hue + 0.5) % 1.0, self.saturation)

            mask_a = self.apply_color(mask_a, color_a)
            mask_b = self.apply_color(mask_b, color_b)
            self.frame = ((mask_a + mask_b)/2).astype(np.uint8)

        else:
            mask = np.clip(((mask_a  * 0.5 + mask_b * 0.5)).astype(np.uint8), 0, 255)
            color = (self.animation_settings.red, self.animation_settings.green, self.animation_settings.blue)
            self.frame = self.apply_color(mask, color)

        return self.frame


class Starfield(Animator):
    def __init__(self, animation_settings : AnimationSettings):
        #call base constructor
        super().__init__(animation_settings)
     
        self.num_stars = 10

        # Possible sizes
        self.options = [1, 2, 3]
        # Probabilities (must sum to 1.0)
        self.probs = [0.60, 0.3, 0.10]

        # Star positions
        self.x_positions = np.random.randint(0, 64, self.num_stars)
        self.y_positions = np.random.randint(0, 64, self.num_stars)

        # Individual star properties
        self.brightness = np.random.uniform(0.0, 1.0, self.num_stars)
        self.speeds = np.random.uniform(0.002, 0.02, self.num_stars)
        self.brightness_direction = np.random.randint(0, 2, self.num_stars)        
        self.sizes = np.random.choice(self.options,self.num_stars, p=self.probs)

    def get_next_frame(self):
        # Deep night background
        mask = np.zeros((64, 64, 4), dtype=np.uint8)
        mask[..., 3] = 255
        lights = np.zeros((64, 64, 4))
        lights[..., 3] = 255

        for i in range(self.num_stars):
            #check fade direction and fade brightness
            if self.brightness_direction[i] >= 1:
                self.brightness[i] += self.speeds[i] * self.animation_settings.animation_speed
                self.brightness[i] = min(self.brightness[i], 1.0)
            else:
                self.brightness[i] -= self.speeds[i] * self.animation_settings.animation_speed
                self.brightness[i] = max(self.brightness[i], 0)

            #when max brightness is reached 
            if self.brightness[i] >= 1.0:
                self.brightness_direction[i] = 0

            #when min brightness is reached
            if self.brightness_direction[i] == 0 and self.brightness[i] <= 0.0:
                #generate a new star
                self.x_positions[i] = np.random.randint(0, 64)
                self.y_positions[i] = np.random.randint(0, 64)
                self.brightness[i] = 0
                self.speeds[i] = np.random.uniform(0.002, .02)
                self.brightness_direction[i] = 1
                self.sizes[i] = np.random.choice(self.options, p=self.probs)

            #add star to the mask
            x_start = self.x_positions[i]
            x_end = min(x_start + self.sizes[i], 64 -1)
            y_start = self.y_positions[i]
            y_end = min(y_start + self.sizes[i], 64 -1)

            lights[x_start:x_end, y_start:y_end, 0:3] += self.brightness[i] * 255
        mask = np.clip(lights, 0, 255).astype(np.uint8)
        self.color_mask(mask)
        return self.frame



class SlowClock(Animator):
    def __init__(self, animation_settings : AnimationSettings):
        #call base constructor
        super().__init__(animation_settings)

        # Load the font
        self.font = ImageFont.truetype("Fonts/Sono-VariableFont_MONO,wght.ttf", size=20)


    def draw_centered_text(self, draw:ImageDraw.Draw, text:str, rect:tuple):
        """
        draw: PIL.ImageDraw object
        text: string to draw
        rect: tuple (left, top, right, bottom)
        """


        x0, y0, x1, y1 = rect
        rect_width = x1 - x0
        rect_height = y1 - y0

        # getbbox returns (left, top, right, bottom)
        bbox = draw.textbbox((0, 0), text, font=self.font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]


        # Calculate centered position
        bbox = draw.textbbox((0, 0), text, font=self.font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = x0 + (rect_width - text_width) / 2
        y = y0 + (rect_height - text_height) / 2 - bbox[1] # Subtract offset

        draw.text((x, y), text, font=self.font, fill=(255,255,255))


    def get_next_frame(self):
        time = datetime.now()

        # Render text
        img = Image.new("L", (64, 64), 0).convert("RGBA")
        draw = ImageDraw.Draw(img)
        draw.fontmode = "1"
        #draw times on image
        self.draw_centered_text(draw, time.strftime("%H"), (0,6,63, 21))
        self.draw_centered_text(draw, time.strftime("%M"), (0,24,63, 39))
        self.draw_centered_text(draw, time.strftime("%S"), (0,42,63, 57))

        mask = np.array(img).astype(np.uint8)

        #color the image
        self.color_mask(mask)
        return self.frame
