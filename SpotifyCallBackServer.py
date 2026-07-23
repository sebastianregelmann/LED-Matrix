import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
from dataclasses import dataclass
import time


@dataclass 
class CallbackResponse:
    code: str | None = None
    state: str | None = None
    error: str | None = None

class CallbackHandler:
    def __init__(self, host: str, port: int, path: str):
        self.path = path
        self.response = None
        self.server = None
        
        # Create a reference to this instance to use inside the inner class
        parent = self

        class RequestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                # Only handle the specific path provided
                if self.path.startswith(parent.path):
                    parsed = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Update the response dataclass
                    code = params.get('code', [None])[0]
                    state = params.get('state', [None])[0]
                    error = params.get('error', [None])[0]

                    parent.response = CallbackResponse(code, state, error)
                    
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Authorization successful. You can close this window.")
                    print("Call Back server received Credentials")
                else:
                    self.send_response(404)
                    self.end_headers()

            # Silence the default logging
            def log_message(self, format, *args):
                return

        self.server = HTTPServer((host, port), RequestHandler)
        
        # Run server in a background thread
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        print("Call Back Server started")

    def shutdown(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def wait_for_code(self) ->str:
        while(self.response == None):
            time.sleep(0.1)

        self.shutdown()

        if(self.response.error != None):
            print("Callback Server Error: ", self.response.error)
            return self.response.error
        
        return self.response.code
    

