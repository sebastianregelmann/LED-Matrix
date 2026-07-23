import requests
from pathlib import Path
from dataclasses import dataclass
import json
from datetime import datetime
import secrets
import urllib.parse
import webbrowser
from SpotifyCallBackServer import CallbackHandler
import base64
import sys

@dataclass
class Tokens:
    client_id : str
    client_secret: str
    refresh_token : str
    access_token : str

@dataclass
class TokenAliveTime:
    time_stamp : datetime
    alive_time : int


# Load the token from the json file
print("Loading Spotify API Keys")
with open(Path("SpotifyTokens/APIKeys.json"), 'r') as file:
    data = json.load(file)
    client_id = data["ClientID"]
    client_secret = data["ClientSecret"]
    redirect_url = data["RedirecteURL"]

print("Token loaded")
print("Client ID: ", client_id)
print("Client Secret: ", client_secret)
print("Redirect URL: ", redirect_url)

# Parse host, port, and path dynamically from redirect_url
parsed_url = urllib.parse.urlparse(redirect_url)
cb_host = parsed_url.hostname or '127.0.0.1'
cb_port = parsed_url.port or 8888
cb_path = parsed_url.path if parsed_url.path else '/callback'

print("Redirect to authentication site")
# Create state token
state = secrets.token_urlsafe(18)

# Create authentication url
query = urllib.parse.urlencode(
    {
        "response_type": "code",
        "client_id": client_id,
        "scope": "user-read-playback-state",
        "redirect_uri": redirect_url,
        "state": state
    }
)
        
auth_url = f"https://accounts.spotify.com/authorize?{query}"
webbrowser.open(auth_url)

print(f"Starting Redirect Server on {cb_host}:{cb_port}{cb_path} ...")
handler = CallbackHandler(cb_host, cb_port, cb_path)

# Wait for the callback server to get code
refresh_token = handler.wait_for_code()
print("Received refresh token from Call Back Server: ", refresh_token)

# Check back the code with spotify api
credentials = f"{client_id}:{client_secret}".encode("utf-8")
basic_auth = base64.b64encode(credentials).decode("ascii")

body = {
    "grant_type": "authorization_code",
    "code": refresh_token,
    "redirect_uri": redirect_url
}
headers = {
    "Authorization": f"Basic {basic_auth}",
    "Content-Type": "application/x-www-form-urlencoded"
}

print("Authenticate refresh token ...")
response = requests.post(url="https://accounts.spotify.com/api/token", headers=headers, data=body)

if response.status_code != 200:
    print("Error authenticating user: ", response.status_code)
    print(response.text)
    sys.exit()

print("Authentication successful")

# Reading credentials from response
data = json.loads(response.text)
access_token = data["access_token"]
refresh_token = data["refresh_token"]
time_stamp = datetime.now()
alive_time = data["expires_in"]
print("New Refresh Token: ", refresh_token)
print("New Access Token: ", access_token)

# Saving tokens in TokenCache.json
print("Saving Credentials to cache file")
cache_data = {
    "ClientID": client_id,
    "ClientSecret": client_secret,
    "RefreshToken": refresh_token,
    "AccessToken": access_token,
    "TimeStamp": time_stamp.strftime("%Y-%m-%d %H:%M:%S"),
    "AliveTime": alive_time
}

with open("SpotifyTokens/TokenCache.json", 'w', encoding='utf-8') as file:
    json.dump(cache_data, file, indent=4)

print("Successfully saved tokens to SpotifyTokens/TokenCache.json")