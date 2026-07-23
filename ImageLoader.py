import os
from PIL import Image
import numpy as np

ABSOLUTE_PATH = "/home/pi/LED-Matrix"

ANIMATOR_MISSING_PATH = "ErrorImages/Animation/AnimatorNotFound.png"
GIF_MISSING_PATH = "ErrorImages/GIFS/GifNotFound.png"
IMAGE_MISSING_PATH = "ErrorImages/StaticImage/ImageNotFound.png"
SPOTIFY_MSSING_API_KEYS = "ErrorImages/Spotify/APIKeysNotFound.png"
SPOTIFY_INVALID_REFRESH_TOKEN = "ErrorImages/Spotify/RefreshTokenInvalid.png"#
SPOTIFY_REQUEST_FAILURE = "ErrorImages/Spotify/RequestFailure.png"
SPOTIFY_ICON = "ErrorImages/Spotify/SpotifyIcon.png"
SPOTIFY_UNKNOWN_ERROR = "ErrorImages/Spotify/UnknownError.png"



def load_image( path:str) -> np.ndarray:
    abs_path = os.path.join(ABSOLUTE_PATH, path)
    if os.path.exists(abs_path):
        img = Image.open(abs_path).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
        return np.array(img).dtype(np.uint8)


def load_animator_missing() -> np.ndarray:
    return load_image(ANIMATOR_MISSING_PATH)

def load_gif_missing() -> np.ndarray:
    return load_image(GIF_MISSING_PATH)

def load_image_missing() -> np.ndarray:
    return load_image(IMAGE_MISSING_PATH)

def load_spotify_missing_api_key() -> np.ndarray:
    return load_image(SPOTIFY_MSSING_API_KEYS)

def load_spotify_invalid_refresh_token () -> np.ndarray:
    return load_image(SPOTIFY_INVALID_REFRESH_TOKEN)

def load_spotify_request_failure () -> np.ndarray:
    return load_image(SPOTIFY_REQUEST_FAILURE)

def load_spotify_icon () -> np.ndarray:
    return load_image(SPOTIFY_ICON)

def load_spotify_unknown_error () -> np.ndarray:
    return load_image(SPOTIFY_UNKNOWN_ERROR)
