from FrameDriver import FrameDriver
from http.server import ThreadingHTTPServer
from LEDMatrixServer import SimpleHandler
import threading
import time
import argparse

#import cv2 


# Thread to run the server
def run_server(frame_driver: FrameDriver, port=8000):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, SimpleHandler)

    httpd.frame_driver = frame_driver

    print(f"Starting server on port {port}...")
    httpd.serve_forever()

# Thread for debug GUI
# def gui_loop(frame_driver: FrameDriver):
#     while True:
#         # "Pull" the current frame
#         current_frame = frame_driver.led_driver.frame.copy()
            
#         # Display it
#         image_cv = cv2.cvtColor(current_frame, cv2.COLOR_RGBA2BGRA)
#         cv2.imshow("Test", cv2.resize(image_cv, (512, 512), interpolation=cv2.INTER_NEAREST))
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break


if __name__ == "__main__":
    #check if frame driver should save status
    # 1. Initialize parser
    parser = argparse.ArgumentParser()

    # 2. Add the flag (action="store_true" means if it's present, it's True; otherwise, False)
    parser.add_argument("--save-status", action="store_true", help="Enable status saving")

    # 3. Parse arguments
    args = parser.parse_args()

    save_status = False
    # 4. Check the flag
    if args.save_status:
        save_status = True

    #led_driver = LEDMatrixDriver(127)
    frame_driver = FrameDriver(save_status)

    #Start HTTP Server
    server_thread = threading.Thread(target=run_server, args=(frame_driver, 8000), daemon=True)
    server_thread.start()
    
    # Start the GUI thread BEFORE starting the server
    #threading.Thread(target=gui_loop,args=(frame_driver,), daemon=True).start()

    #keep alive
    while True:
        time.sleep(10)




