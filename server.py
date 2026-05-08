import http.server
import urllib.request
import urllib.error
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"token": "", "country": "no", "language": "no"}

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f)

config = load_config()
CIDER = "http://localhost:10767"

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/settings/config":
            self.send_json(200, {
                "country": config.get("country", "no"),
                "language": config.get("language", "no"),
                "hasToken": bool(config.get("token"))
            })
        elif self.path.startswith("/api/"):
            self.proxy("GET", None)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/settings/config":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            if "token" in body and body["token"]:
                config["token"] = body["token"]
            if "country" in body:
                config["country"] = body["country"]
            if "language" in body:
                config["language"] = body["language"]
            save_config(config)
            self.send_json(200, {"status": "ok"})
        elif self.path.startswith("/api/"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            self.proxy("POST", body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def proxy(self, method, body):
        if not config.get("token"):
            self.send_json(401, {"error": "no_token"})
            return
        url = CIDER + self.path
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("apptoken", config["token"])
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                data = r.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass

os.chdir(os.path.dirname(os.path.abspath(__file__)))
print("Cider Remote proxy kjører på http://0.0.0.0:8080")
http.server.HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
