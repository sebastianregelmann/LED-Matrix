import requests
from pathlib import Path
from dataclasses import dataclass
import time
import json
from datetime import datetime
import base64
import numpy as np
from PIL import Image
from io import BytesIO
import threading
import os


@dataclass
class APIKeys:
    client_id: str | None
    client_secret: str | None
    refresh_token: str | None
    access_token: str | None
    time_stamp: datetime | None
    alive_time: int | None


@dataclass
class PlaybackInfo:
    song_id: str | None
    is_playing: bool | None
    progress: int | None
    duration: int | None
    cover: np.ndarray | None


class Client():
    tokens: APIKeys | None
    current_playback_info: PlaybackInfo
    request_timeout: float
    
    lock: threading.Lock
    request_thread: threading.Thread | None
    stop_event: threading.Event
    session: requests.Session

    spotify_icon: np.ndarray
    no_api_keys_image: np.ndarray
    unknown_error: np.ndarray
    refresh_token_invalid: np.ndarray
    request_failure : np.ndarray

    def __init__(self, request_timeout: float):
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.request_thread = None
        self.session = requests.Session()

        # Load Cached Tokens
        self.load_tokens()

        # Create Startup Playback Info
        background = np.zeros((64, 64, 4), dtype=np.uint8)
        background[..., 3] = 255
        self.current_playback_info = PlaybackInfo("NotStarted", None, None, None, background)
        self.request_timeout = request_timeout

        # Load error Images
        self.load_error_images()

        print("[SPOTIFY CLIENT] Client is ready to start")

    def start_request_thread(self):
        if self.tokens is None:
            print("[SPOTIFY CLIENT] API Keys not Loaded")
            with self.lock:
                self.current_playback_info = PlaybackInfo("NO_API_KEYS", None, None, None, self.no_api_keys_image)
            return       
        
        if self.request_thread is not None and self.request_thread.is_alive():
            print("[SPOTIFY CLIENT] Request thread already running")
            return
        
        # Check if current refresh token is valid by requesting a new access token
        response = self.request_new_access_token()
        if response.status_code == 503:
            with self.lock:
                self.current_playback_info = PlaybackInfo(f"RESPONSE_ERROR: {response.status_code}", None, None, None, self.request_failure)
            return
        
        elif response.status_code != 200:
            print("[SPOTIFY CLIENT] Can't refresh Access Token on start")
            print("[SPOTIFY CLIENT] Code:", response.status_code)
            print("[SPOTIFY CLIENT] Response Message:", response.text)
            with self.lock:
                self.current_playback_info = PlaybackInfo(f"RESPONSE_ERROR: {response.status_code}", None, None, None, self.refresh_token_invalid)
            return    
        
        # Start the Request Loop
        print("[SPOTIFY CLIENT] Starting Request Thread")
        self.stop_event.clear()
        self.request_thread = threading.Thread(target=self.request_loop, daemon=True)
        self.request_thread.start()

    def request_loop(self):
        print("[SPOTIFY CLIENT] Started Request Thread")
        while not self.stop_event.is_set():    
            # Check if token needs refreshing
            if self.tokens and self.tokens.time_stamp:
                time_dif = datetime.now() - self.tokens.time_stamp
                if time_dif.total_seconds() > (self.tokens.alive_time or 3600) - 60:
                    print("[SPOTIFY CLIENT] Access Token expiring, requesting new one...")
                    response = self.request_new_access_token()
                    
                    # 503 indicates transient network error — retry next cycle without stopping
                    if response.status_code == 503:
                        print("[SPOTIFY CLIENT] Network error while refreshing token. Retrying next cycle...")
                        with self.lock:
                            self.current_playback_info = PlaybackInfo(f"RESPONSE_ERROR: {response.status_code}", None, None, None, self.request_failure)

                        time.sleep(self.request_timeout)
                        continue
                    elif response.status_code != 200:
                        with self.lock:
                            self.current_playback_info = PlaybackInfo(f"RESPONSE_ERROR: {response.status_code}", None, None, None, self.refresh_token_invalid)
                        self.stop_event.set()
                        print(f"[SPOTIFY CLIENT] Fatal Error Requesting Access Token ({response.status_code}): {response.text}")
                        continue

            # Request current playback state
            playback_response = self.request_playback_info()

            # Transient Connection Error (Wi-Fi drop/timeout)
            if playback_response.status_code == 503:
                print("[SPOTIFY CLIENT] Temporary network error. Waiting to retry...")
                with self.lock:
                    self.current_playback_info = PlaybackInfo(f"RESPONSE_ERROR: {playback_response.status_code}", None, None, None, self.request_failure)
                time.sleep(self.request_timeout)
                continue

            # No Player Active
            if playback_response.status_code == 204:
                with self.lock:
                    self.current_playback_info = PlaybackInfo("No_Player_Active", False, None, None, self.spotify_icon)
                time.sleep(self.request_timeout)
                continue
            
            # Access Token Expired
            if playback_response.status_code == 401:
                print("[SPOTIFY CLIENT] Access Token invalid. Requesting new one...")
                response = self.request_new_access_token()
                if response.status_code == 503:
                    with self.lock:
                        self.current_playback_info = PlaybackInfo(f"RESPONSE_ERROR: {response.status_code}", None, None, None, self.request_failure)
                    time.sleep(self.request_timeout)
                    continue
                elif response.status_code != 200:
                    with self.lock:
                        self.current_playback_info = PlaybackInfo(f"RESPONSE_ERROR: {response.status_code}", None, None, None, self.refresh_token_invalid)
                    self.stop_event.set()
                    print(f"[SPOTIFY CLIENT] Fatal Error Requesting Access Token ({response.status_code}): {response.text}")
                    continue
                continue

            # Forbidden / Refresh Token Invalidated
            if playback_response.status_code == 403: 
                print("[SPOTIFY CLIENT] Refresh Token invalid or scope forbidden")
                with self.lock:
                    self.current_playback_info = PlaybackInfo(f"RESPONSE_ERROR: {playback_response.status_code}", None, None, None, self.refresh_token_invalid)
                self.stop_event.set()
                continue
            
            # Rate Limited
            if playback_response.status_code == 429:
                retry_after = int(playback_response.headers.get("Retry-After", "20"))
                print(f"[SPOTIFY CLIENT] Rate limited. Waiting for {retry_after} seconds")
                time.sleep(retry_after)
                continue
            
            # Catch-all for unhandled status codes
            if playback_response.status_code != 200: 
                print(f"[SPOTIFY CLIENT] Unexpected Code {playback_response.status_code}: {playback_response.text}")
                with self.lock:
                    self.current_playback_info = PlaybackInfo(f"RESPONSE_ERROR: {playback_response.status_code}", None, None, None, self.unknown_error)
                time.sleep(2)
                continue

            # Parse and update playback data
            self.handle_playback_response(playback_response)
            time.sleep(self.request_timeout)

        print("[SPOTIFY CLIENT] Request Thread Stopped")

    def load_tokens(self):
        token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SpotifyTokens", "TokenCache.json")
        if os.path.exists(token_path) == False:
            print("[SPOTIFY CLIENT] TokenCache.json not found.")
            self.tokens = None
            return

        try:
            with open(token_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.tokens = APIKeys(
                    client_id=data["ClientID"],
                    client_secret=data["ClientSecret"],
                    refresh_token=data["RefreshToken"],
                    access_token=data["AccessToken"],
                    time_stamp=datetime.strptime(data["TimeStamp"], "%Y-%m-%d %H:%M:%S"),
                    alive_time=data["AliveTime"]
                )
        except Exception as e:
            print(f"[SPOTIFY CLIENT] Can't load API Keys: {e}")
            self.tokens = None

    def save_tokens(self):
        if not self.tokens:
            return

        data = {
            "ClientID": self.tokens.client_id,
            "ClientSecret": self.tokens.client_secret,
            "RefreshToken": self.tokens.refresh_token,
            "AccessToken": self.tokens.access_token,
            "TimeStamp": self.tokens.time_stamp.strftime("%Y-%m-%d %H:%M:%S") if self.tokens.time_stamp else "",
            "AliveTime": self.tokens.alive_time
        }

        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SpotifyTokens")
        os.makedirs(path, exist_ok=True)
        
        target_file = os.path.join(path, "TokenCache.json")
        
        with open(target_file, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

    def handle_refresh_access_token_response(self, response: requests.Response):
        try:
            data = response.json()
            if self.tokens:
                self.tokens.access_token = data["access_token"]
                self.tokens.time_stamp = datetime.now()
                self.tokens.alive_time = data.get("expires_in", 3600)

                if "refresh_token" in data:
                    self.tokens.refresh_token = data["refresh_token"]

                self.save_tokens()
        except Exception as e:
            print(f"[SPOTIFY CLIENT] Error parsing refresh token response: {e}")

    def request_new_access_token(self) -> requests.Response:
        if not self.tokens:
            res = requests.Response()
            res.status_code = 400
            res._content = b"No API Keys initialized"
            return res

        try:
            url = "https://accounts.spotify.com/api/token"
            credentials = f"{self.tokens.client_id}:{self.tokens.client_secret}".encode("utf-8")
            basic_auth = base64.b64encode(credentials).decode("ascii")
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {basic_auth}"
            } 
            body = {
                "grant_type": "refresh_token",
                "refresh_token": f"{self.tokens.refresh_token}"
            }
            
            response = self.session.post(url=url, headers=headers, data=body, timeout=10)

            if response.status_code == 200:
                self.handle_refresh_access_token_response(response)

            return response
        
        except Exception as e:
            # 503 Service Unavailable flags transient connection issues to loop
            response = requests.Response()
            response.status_code = 503
            response._content = f"Connection error while requesting Access Token: {e}".encode("utf-8")
            return response

    def get_album_cover(self, url: str | None) -> np.ndarray:
        if not url:
            return self.spotify_icon

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            img = Image.open(BytesIO(response.content))
            if img.width != 64 or img.height != 64:
                img = img.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)

            return np.array(img)

        except Exception as e:
            print(f"[SPOTIFY CLIENT] Error downloading image: {e}")
            return self.spotify_icon

    def get_nested(self, data, keys):
        for key in keys:
            try:
                if isinstance(data, dict) and key in data:
                    data = data[key]
                elif isinstance(data, list) and isinstance(key, int) and 0 <= key < len(data):
                    data = data[key]
                else:
                    return None
            except (IndexError, TypeError):
                return None
        return data

    def handle_playback_response(self, response: requests.Response):
        try:
            data = response.json()
        except Exception as e:
            print(f"[SPOTIFY CLIENT] JSON parse error: {e}")
            return

        is_playing = self.get_nested(data, ["is_playing"])
        progress = self.get_nested(data, ["progress_ms"])
        currently_playing_type = self.get_nested(data, ["currently_playing_type"])

        if currently_playing_type == "track":
            song_id = self.get_nested(data, ["item", "id"])
            duration = self.get_nested(data, ["item", "duration_ms"])
            cover_url = self.get_nested(data, ["item", "album", "images", 2, "url"])
        elif currently_playing_type == "episode":
            song_id = self.get_nested(data, ["item", "id"])
            duration = self.get_nested(data, ["item", "duration_ms"])
            cover_url = self.get_nested(data, ["item", "images", 2, "url"])
        else:
            song_id = None
            duration = None
            cover_url = None

        cover = None
        if song_id != self.current_playback_info.song_id:
            cover = self.get_album_cover(cover_url)
            print("[SPOTIFY CLIENT] New Song is playing")

        with self.lock:
            if cover is None:
                cover = self.current_playback_info.cover
            self.current_playback_info = PlaybackInfo(song_id, is_playing, progress, duration, cover)

    def request_playback_info(self) -> requests.Response:
        if not self.tokens or not self.tokens.access_token:
            res = requests.Response()
            res.status_code = 401
            res._content = b"No Access Token Available"
            return res

        try:
            url = "https://api.spotify.com/v1/me/player?additional_types=episode"
            headers = {
                "Authorization": f"Bearer {self.tokens.access_token}"
            }
            return self.session.get(url=url, headers=headers, timeout=10)
        except Exception as e:
            # 503 Service Unavailable flags transient connection issues to loop
            response = requests.Response()
            response.status_code = 503
            response._content = f"Connection error while requesting Playback Info: {e}".encode("utf-8")
            return response

    def stop_request_thread(self):
        print("[SPOTIFY CLIENT] Stopping request thread...")
        self.stop_event.set()
        if self.request_thread is not None and self.request_thread.is_alive():
            self.request_thread.join(timeout=5)


    def get_playback_info(self) -> PlaybackInfo:
        with self.lock:
            return self.current_playback_info


    def load_error_images(self):
        def load_img(path: str) -> np.ndarray:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Construct a clean, absolute string path directly
            file_path = os.path.join(current_dir, "ErrorImages", "Spotify", path)
            
            # Use os.path instead of pathlib to avoid proxy exceptions
            if os.path.exists(file_path):
                img = Image.open(file_path).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
                return np.array(img)
            
            # Fallback black canvas if missing
            bg = np.zeros((64, 64, 4), dtype=np.uint8)
            bg[..., 3] = 255
            return bg

        self.spotify_icon = load_img("SpotifyIcon.png")
        self.unknown_error = load_img("UnknownError.png")
        self.no_api_keys_image = load_img("APIKeysNotFound.png")
        self.refresh_token_invalid = load_img("RefreshTokenInvalid.png")
        self.request_failure = load_img("RequestFailure.png")