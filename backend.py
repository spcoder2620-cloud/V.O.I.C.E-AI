#!/usr/bin/env python3
"""V.O.I.C.E. HTTP backend for GitHub Pages / Render."""
import contextlib
import io
import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from voice import Voice

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8765"))

# One brain instance per server process so conversation context and
# learned topics remain available while the process is alive.
brain = Voice()


def run_voice(message):
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        reply = brain.respond(message)
    return str(reply or ""), captured.getvalue().strip()


class Handler(BaseHTTPRequestHandler):
    server_version = "VOICE/1.0"

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/health":
            self.send_json(200, {
                "ok": True,
                "service": "V.O.I.C.E.",
                "brain": "online",
                "endpoint": "/chat"
            })
            return
        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/chat":
            self.send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1024 * 1024:
                raise ValueError("Invalid request size.")

            data = json.loads(self.rfile.read(length).decode("utf-8"))
            message = data.get("message")
            if not isinstance(message, str) or not message.strip():
                raise ValueError("'message' must be a non-empty string.")
            message = message.strip()
            if len(message) > 10000:
                raise ValueError("Message is too long.")

            print(f"\\nYOU: {message}")
            reply, research = run_voice(message)
            print(f"V.O.I.C.E.: {reply}")

            self.send_json(200, {
                "reply": reply,
                "research": research
            })
        except Exception as exc:
            traceback.print_exc()
            self.send_json(500, {"error": str(exc)})


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print("V . O . I . C . E .")
    print("Python backend ........ ONLINE")
    print(f"Listening ............. http://{HOST}:{PORT}")
    print("GET  /health")
    print("POST /chat")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
