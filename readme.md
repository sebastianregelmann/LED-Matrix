# Installation
1. Clone
2. Create venv
3. install requirements


4. Install rgb matrix
5. pip3 install rgbmatrix

sudo apt-get update
sudo apt-get install -y build-essential python3-dev cython3cd 
sudo apt-get install -y python3.13-dev python3-dev build-essential
sudo apt-get install python3-pil
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd ~/rpi-rgb-led-matrix
source /home/pi/LED-Matrix/venv/bin/activate
pip install .


3. dtparam=audio=off disable audio in /boot/firmware/config.txt
sudo nano /etc/modprobe.d/alsa-blacklist.conf
blacklist snd_bcm2835
save and exit

6. disable port firewall (if installed) for access in Lan
sudo ufw allow 8000/tcp


# Autheticate User
1. SSH with portforwading 
ssh -L 8000:localhost:8000 pi@RGBMatrixPi
2. copy SpotifyTokens/APIKeys-Example.json to SpotifyTokens/APIKeys.json
3. Insert own API Keys into the file
4. Activate Enviroment
5. Start AuthenticateSpotify.py
6. Follow instructions in the terminal
7. Successfull if /SpotifyTokens/TokenChache.json exists




# Starting main code
sudo /home/pi/LED-Matrix/venv/bin/python /home/pi/LED-Matrix/your_script.py




cd /home/pi/LED-Matrix

# 1. Give read/write/execute permissions to all directories recursively
find . -type d -exec chmod 775 {} +

# 2. Give read/write permissions to all files recursively
find . -type f -exec chmod 664 {} +

# 3. Ensure your user owns every single file and folder
sudo chown -R pi:pi /home/pi/LED-Matrix