# Raspberry Pi RGB LED Matrix Controller

A Python-based application to control an RGB LED Matrix attached to a Raspberry Pi. Includes support for custom image rendering, animated GIFs, generative visualizers, live Spotify cover art/metadata integration, and remote control via HTTP or MQTT APIs (with Home Assistant integration).

---

## 📌 Features

- 🖼️ **Image Display:** Load and display static images scaled to matrix dimensions.
- 🎞️ **GIF Playback:** Render animated GIFs and multi-frame images.
- 🌀 **7 Generative Animation Modes:**
  - `RAIN` – Dynamic falling rain effect
  - `FIRE` – Animated fire and smoke simulation
  - `PLASMA` – Flowing color noise
  - `LAVALAMP` – Fluid lava lamp visuals
  - `DRIFTING_FOG` – Soft shifting atmospheric noise
  - `STARFIELD` – Twinkling background stars
  - `CLOCK` – Real-time digital clock overlay
  - *All modes support customizable animation speed, static color, and color fading settings.*
- 🎵 **Spotify Integration:** Display real-time cover art and track progress with 4 display profiles:
  - `DISC` – Animated spinning vinyl disc (pauses when playback is paused)
  - `COVER` – Static cover art display
  - `DISC_TIME` – Spinning vinyl disc with dynamic track progress bar
  - `COVER_TIME` – Static cover art with dynamic track progress bar
- 🎛️ **Remote Control:** Full state management via HTTP REST API and MQTT broker integration.

---

## 📋 Table of Contents
- [Raspberry Pi RGB LED Matrix Controller](#raspberry-pi-rgb-led-matrix-controller)
  - [📌 Features](#-features)
  - [📋 Table of Contents](#-table-of-contents)
  - [🛠️ Prerequisites \& Hardware Config](#️-prerequisites--hardware-config)
  - [📥 Installation](#-installation)
    - [1. Clone \& Setup Repository](#1-clone--setup-repository)
    - [2. Install Matrix Hardware Library (`rpi-rgb-led-matrix`)](#2-install-matrix-hardware-library-rpi-rgb-led-matrix)
  - [⚙️ Configuration](#️-configuration)
    - [Main Parameters](#main-parameters)
    - [Command-Line Arguments \& Startup](#command-line-arguments--startup)
  - [🎧 Spotify Setup](#-spotify-setup)
  - [🖼️ Usage \& Media Assets](#️-usage--media-assets)
  - [🌐 API Reference](#-api-reference)
    - [Mode Priority Hierarchy](#mode-priority-hierarchy)
    - [HTTP API](#http-api)
    - [MQTT API](#mqtt-api)
  - [🏠 Home Assistant Integration](#-home-assistant-integration)

---

## 🛠️ Prerequisites & Hardware Config

Before installing software packages, configure your Raspberry Pi kernel settings to prevent onboard audio hardware conflicts with matrix GPIO timing.

```bash
# 1. Disable onboard audio in boot config
sudo nano /boot/firmware/config.txt
# Add this parameter or change it to off:
dtparam=audio=off

# 2. Blacklist ALSA audio module
sudo nano /etc/modprobe.d/alsa-blacklist.conf
# Add this parameter:
blacklist snd_bcm2835

# 3. Reboot system to apply changes
sudo reboot now
```

---

## 📥 Installation

### 1. Clone & Setup Repository
```bash
# Move into home directory
cd ~

# Clone the repository
git clone https://github.com/sebastianregelmann/LED-Matrix.git

# Move into repository directory
cd LED-Matrix

# Create a virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r "requirements.txt"
```

### 2. Install Matrix Hardware Library (`rpi-rgb-led-matrix`)
```bash
# Move to home directory
cd ~

# Clone repository
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git

# Move to repository directory
cd rpi-rgb-led-matrix

# Install build dependencies
sudo apt-get update
sudo apt-get install -y python3-dev build-essential python3-pil cython3

# Activate venv of LED-Matrix repository
source ../LED-Matrix/venv/bin/activate

# Install the library inside the venv
pip install .
```

---

## ⚙️ Configuration

### Main Parameters
In `main.py`, configure the parameters at the top of the file to match your setup:

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `HTTP_PORT` | `int` | Port used for the HTTP server |
| `MQTT_ADDRESS` | `str` | IP address or domain of the MQTT broker |
| `MQTT_PORT` | `int` | Port of the MQTT broker |
| `MQTT_TOPIC_LISTEN` | `str` | MQTT topic the client listens to for status updates |
| `MQTT_TOPIC_PUBLISH` | `str` | MQTT topic the client publishes status updates to |
| `MQTT_USER` | `str / None` | Username if MQTT server uses authentication (else `None`) |
| `MQTT_PWD` | `str / None` | Password if MQTT server uses authentication (else `None`) |

### Command-Line Arguments & Startup
Because `rpi-rgb-led-matrix` requires `sudo` privileges to interact with GPIO pins, start the script using the full path to your virtual environment's Python interpreter:

```bash
sudo /home/username/LED-Matrix/venv/bin/python  /home/username/LED-Matrix/main.py [FLAGS]
```

**Available Startup Flags:**
* `--save-status` : Enables caching of the current state to `StatusCache/Status.json` on changes and loads the last configuration on startup.  
  > [!WARNING]
  > Not recommended for long-term production use due to high SD card write wear.
* `--disable-http` : Disables the HTTP Server.
* `--disable-mqtt` : Disables the MQTT Client.

---

## 🎧 Spotify Setup

To enable Spotify cover art integration, set up access to the Spotify Web API:

1. Create an application in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Add `http://127.0.0.1:8888/callback` as a **Redirect URI** in your app settings.
3. Open `SpotifyTokens/APIKeys-Example.json`, populate your `Client ID` and `Client Secret` values, save the file, and rename it to `APIKeys.json`.
4. Connect to your Raspberry Pi using SSH port forwarding:
   ```bash
   ssh -L 8888:127.0.0.1:8888 user@hostname
   ```
5. Navigate to the repository and activate the virtual environment:
   ```bash
   cd ~/LED-Matrix
   source venv/bin/activate
   ```
6. Run the authentication script and follow the on-screen instructions:
   ```bash
   python3 AuthenticateSpotify.py
   ```
7. Upon successful authentication, `SpotifyTokens/SpotifyCache.json` will be created. Tokens are valid for **180 days**, after which you will need to re-authenticate.

---

## 🖼️ Usage & Media Assets

To add custom media:
1. Place static images into the `IMAGES/` folder or animated GIFs into the `GIF/` folder. Most common image formats are supported.
2. Load an image or GIF by providing its filename in the JSON payload sent via HTTP or MQTT (see `StatusCache/Status.json` for structure).

---

## 🌐 API Reference

### Mode Priority Hierarchy
If multiple modes are enabled in a state update payload, priority is resolved in the following order:
$$	{Spotify} \longrightarrow 	{Animation} \longrightarrow 	{GIF} \longrightarrow {Image}$$

### HTTP API

* **`GET http://<hostname>:<port>/status`**  
  Returns a JSON string representing the current state of the matrix (structured like `StatusCache/Status.json`).

* **`POST http://<hostname>:<port>/changemode`**  
  Accepts a JSON payload (matching the structure of `StatusCache/Status.json`) to update the matrix state.

### MQTT API

* **Publish Topic (`MQTT_TOPIC_PUBLISH`):**  
  The script automatically broadcasts its current status JSON payload upon startup and after receiving state update commands.

* **Listen Topic (`MQTT_TOPIC_LISTEN`):**  
  Publish a message containing a JSON status payload to this topic to update the matrix display.

---

## 🏠 Home Assistant Integration

The `HomeAssistantConfigs/` directory contains configuration templates and automation examples to serve as guidelines for integrating the matrix with Home Assistant via MQTT.