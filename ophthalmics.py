import os
import sys
import subprocess
import socket
import ssl
import http.server
import shutil
import json
import re
from functools import partial

# Configuration
import urllib.request

# Configuration
def get_public_ip():
    try:
        return urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    except Exception:
        print("[!] Could not fetch public IP, falling back to local detection or hardcoded.")
        return "127.0.0.1"

PUBLIC_IP = get_public_ip()
BIND_IP = "0.0.0.0"
HTTP_PORT = 80
HTTPS_PORT = 443
APP_PATH = "/Users/mahmoudsami/.gemini/antigravity/scratch/ophthalmic-infographic-creator"
URL_PATH = "/ophthalmics"

CERT_FILE = "server.crt"
KEY_FILE = "server.key"


def ensure_root():
    """Ensure the script is running with root privileges (needed for IP alias and ports < 1024)."""
    if os.geteuid() != 0:
        print(f"[*] Requesting administrative privileges to bind ports 80/443...")
        try:
            subprocess.check_call(['sudo', sys.executable] + sys.argv)
            sys.exit(0)
        except subprocess.CalledProcessError:
            print("[!] Failed to get root privileges. Exiting.")
            sys.exit(1)


def configure_network_interface():
    """Add the IP alias to lo0 if not already present."""
    print(f"[*] Checking network configuration for {PUBLIC_IP}...")
    
    # Check if IP exists
    try:
        ifconfig_out = subprocess.check_output("ifconfig", shell=True).decode()
        if PUBLIC_IP in ifconfig_out:
            print(f"    [+] IP {PUBLIC_IP} is already configured.")
            return
    except Exception as e:
        print(f"    [!] Error checking interfaces: {e}")

    # Add Alias
    print(f"    [*] Adding IP alias {PUBLIC_IP} to lo0...")
    if sys.platform == "darwin":
        cmd = f"ifconfig lo0 alias {PUBLIC_IP}"
        try:
            subprocess.check_call(cmd, shell=True)
            print("    [+] IP alias added successfully.")
        except subprocess.CalledProcessError as e:
            print(f"    [!] Failed to add IP alias: {e}")
            sys.exit(1)
    else:
        print("    [!] Auto-configuration only supported on macOS.")
        sys.exit(1)


def generate_self_signed_cert():
    """Generate self-signed SSL certificate if missing."""
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return

    print("[*] Generating self-signed SSL certificate...")
    cmd = (
        f'openssl req -x509 -newkey rsa:4096 -nodes -out {CERT_FILE} '
        f'-keyout {KEY_FILE} -days 365 -subj "/CN={PUBLIC_IP}"'
    )
    try:
        subprocess.check_call(cmd, shell=True, stderr=subprocess.DEVNULL)
        print("    [+] Certificate generated.")
    except subprocess.CalledProcessError:
        print("    [!] Failed to generate certificate. Is openssl installed?")
        print("    [!] Continuing with HTTP only if possible...")


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=APP_PATH, **kwargs)

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # 0. Log request
        # print(f"DEBUG: GET {self.path}")

        # 1. Handle API: /api/ftp/status
        if self.path == "/api/ftp/status" or self.path.endswith("/api/ftp/status"):
            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # Return dummy status to silence errors
            self.wfile.write(b'{"running": false, "port": 2121, "host": "127.0.0.1"}')
            return

        # 1.5 Handle API: /api/library/list
        if self.path.endswith("/api/library/list"):
            try:
                lib_dir = os.path.join(APP_PATH, "library")
                items = []
                if os.path.exists(lib_dir):
                    for filename in os.listdir(lib_dir):
                        if filename.endswith(".json"):
                            try:
                                with open(os.path.join(lib_dir, filename), "r") as f:
                                    items.append(json.load(f))
                            except json.JSONDecodeError:
                                pass
                
                self.send_response(200)
                self._send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(items).encode('utf-8'))
            except Exception as e:
                print(f"[!] Error listing library: {e}")
                self.send_error(500, str(e))
            return

        # 2. Redirect root to /ophthalmics/
        if self.path == "/" or self.path == "":
            self.send_response(302)
            self.send_header('Location', URL_PATH + '/')
            self.end_headers()
            return
            
        # 3. Serve Static Files under /ophthalmics
        if self.path == URL_PATH:
            self.send_response(302)
            self.send_header('Location', URL_PATH + '/')
            self.end_headers()
            return

        if self.path.startswith(URL_PATH):
            original_path = self.path
            # Strip prefix to map to filesystem root
            self.path = self.path[len(URL_PATH):]
            if self.path == "":
                self.path = "/"
            
            try:
                super().do_GET()
            finally:
                # Restore path (good practice)
                self.path = original_path
            return
            
        # 4. Fallback/404
        self.send_error(404, f"Not Found: {self.path}")

    def do_POST(self):
        # print(f"DEBUG: POST {self.path}")

        # 1. Handle API: /api/library/upload (Additive)
        if self.path.endswith("/api/library/upload"):
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                # Ensure library dir exists
                lib_dir = os.path.join(APP_PATH, "library")
                os.makedirs(lib_dir, exist_ok=True)
                
                # Parse JSON
                try:
                    library_items = json.loads(post_data)
                except json.JSONDecodeError:
                    print("[!] Invalid JSON payload")
                    self.send_error(400, "Invalid JSON")
                    return
                
                # Write new files (Additive, overwrite if specific ID exists)
                if isinstance(library_items, list):
                    count = 0
                    for item in library_items:
                        safe_title = re.sub(r'[^a-zA-Z0-9]', '_', item.get('title', 'untitled'))[:50]
                        filename = f"{item.get('id', '0')}_{safe_title}.json"
                        with open(os.path.join(lib_dir, filename), "w") as f:
                            json.dump(item, f, indent=2)
                        count += 1
                    print(f"    [+] Uploaded {count} items to library.")
                
                self.send_response(200)
                self._send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"success": true}')
                
            except Exception as e:
                print(f"[!] Error processing POST: {e}")
                self.send_error(500, f"Server Error: {str(e)}")
            return
            
        # 2. Handle API: /api/ftp/start or stop (Dummy)
        if "/api/ftp/" in self.path:
            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success": false, "error": "Not supported in this server mode"}')
            return

        self.send_error(404, f"API Endpoint Not Found: {self.path}")


def run_http_server():
    """Run server on HTTP port 80."""
    server_address = (BIND_IP, HTTP_PORT)
    try:
        httpd = http.server.HTTPServer(server_address, RequestHandler)
        print(f"\n[HTTP] Serving at http://{PUBLIC_IP}{URL_PATH}")
        print(f"[HTTP] (Bound to {BIND_IP}:{HTTP_PORT})")
        httpd.serve_forever()
    except OSError as e:
        print(f"[!] Error starting HTTP server: {e}")


def run_https_server():
    """Run server on HTTPS port 443."""
    if not (os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)):
        print("[!] Missing certificates. Skipping HTTPS.")
        return

    server_address = (BIND_IP, HTTPS_PORT)
    try:
        httpd = http.server.HTTPServer(server_address, RequestHandler)
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        
        print(f"[HTTPS] Serving at https://{PUBLIC_IP}{URL_PATH}")
        print(f"[HTTPS] (Bound to {BIND_IP}:{HTTPS_PORT})")
        httpd.serve_forever()
    except OSError as e:
        print(f"[!] Error starting HTTPS server: {e}")


def main():
    print("=== Ophthalmic Infographic Server Launcher ===")
    
    # 1. Privileges
    ensure_root()
    
    # 2. Network Config
    configure_network_interface()
    
    # 3. Certificates
    generate_self_signed_cert()
    
    # 4. Mode Selection
    print("\nSelect Mode:")
    print(f"1. HTTP (http://{PUBLIC_IP}/ophthalmics)")
    print(f"2. HTTPS (https://{PUBLIC_IP}/ophthalmics)")
    
    # Simple default to HTTP if args provided, else HTTPS
    if len(sys.argv) > 1 and sys.argv[1].lower() == "http":
         run_http_server()
    else:
        # Fork logic to run both? For simplicity in this script, let's just pick one or run thread.
        # Running both in threads is better for the user experience.
        import threading
        
        print("\n[*] Starting servers...")
        
        t1 = threading.Thread(target=run_http_server)
        t1.daemon = True
        t1.start()
        
        try:
            run_https_server()
        except KeyboardInterrupt:
            print("\n[*] Stopping servers...")
            sys.exit(0)

if __name__ == '__main__':
    main()
