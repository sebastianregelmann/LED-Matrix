import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse


class SimpleHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        # 1. Encode the JSON to bytes first to get the true byte-length
        response_body = json.dumps(data).encode("utf-8")
        
        # 2. Send headers
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body))) # <-- Crucial addition
        self.end_headers()
        
        # 3. Write the body
        self.wfile.write(response_body)

    def do_GET(self):
        #pass
        try:
            url = urlparse(self.path)
            path = url.path 

            if path == "/status": 
                frame_driver = self.server.frame_driver 
                status = frame_driver.current_status()     
                self._send_json(status)
                return
            #else
            self._send_json({"error": "Not Found"}, status=404)
        except Exception as e:
            self._send_json({"error": f"Exception: {e} "}, status=500)


    def do_POST(self):
        try:
            url = urlparse(self.path)
            path = url.path 

            if path == "/changemode":
                content_length = int(self.headers.get('Content-Length', 0))
                raw_body = self.rfile.read(content_length) if content_length > 0 else b''
        
                # Parse the JSON right here in the network thread
                payload = json.loads(raw_body.decode('utf-8'))
                
                frame_driver = self.server.frame_driver
                
                # Thread-safely pass the dictionary payload
                frame_driver.handle_mode_change_request(payload)
                
                self._send_json({"status": "success"})
            else: 
                self._send_json({"error": "Not Found"}, status=404)

        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON string received"}, status=400)
        except Exception as e:
            self._send_json({"error": f"Exception{e}"}, status=500)