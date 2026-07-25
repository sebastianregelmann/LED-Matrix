from FrameDriver import FrameDriver
from http.server import ThreadingHTTPServer
from LEDMatrixServer import SimpleHandler
import threading
import time
import argparse
from MQTTClient import MQTTClient
#import cv2 

HTTP_PORT = 8000  #send mode changes as json POST to http://ip:port/changemode receive status as json GET from http://ip:port/status

MQTT_ADDRESS = "ip address"
MQTT_PORT = 1883
MQTT_TOPIC = "/rgbmatrix" #Send mode changes as json to /rgbmatrix receive status at /rgbmatrix/status

# Format of Staus Json in StatusCache/Status.json


# Thread to run the server
def run_server(frame_driver: FrameDriver, port=8000):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, SimpleHandler)

    httpd.frame_driver = frame_driver

    print(f"Starting server on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    #check if frame driver should save status
    # 1. Initialize parser
    parser = argparse.ArgumentParser()

    # 2. Add the flag (action="store_true" means if it's present, it's True; otherwise, False)
    parser.add_argument("--save-status", action="store_true", help="Enable status saving")
    parser.add_argument("--disabel-http", action="store_true", help="Disables the http server")
    parser.add_argument("--disabel-mqtt", action="store_true", help="Disables the mqtt client")

    # 3. Parse arguments
    args = parser.parse_args()

    save_status = False
    # 4. Check the flag
    if args.save_status:
        save_status = True

    #led_driver = LEDMatrixDriver(127)
    frame_driver = FrameDriver(save_status)

    if args.disable_http == False:
        server_thread = threading.Thread(target=run_server, args=(frame_driver, HTTP_PORT), daemon=True)
        server_thread.start()

    if args.disable_mqtt == False:
        # Start the MQTT Client
        mqtt_client = MQTTClient(frame_driver, MQTT_TOPIC, MQTT_ADDRESS, MQTT_PORT)

    #keep alive
    while True:
        time.sleep(10)




