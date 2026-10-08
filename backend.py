#!/usr/bin/env python3
"""
V.O.I.C.E. Python backend for the GitHub Pages frontend.

Endpoints:
    GET  /health
    POST /chat

The server wraps the existing Voice.respond() method.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import contextlib
import io
import json
import os
import threading
import traceback

from voice import Voice


HOST = "0.0.0.0"
PORT = int(
    os.environ.get(
        "PORT",
        "8765"
    )
)

brain = Voice()
brain_lock = threading.Lock()


def run_brain(message):
    """Run the existing brain while capturing its research log."""
    buffer = io.StringIO()

    with brain_lock:
        with contextlib.redirect_stdout(buffer):
            reply = brain.respond(
                message
            )

    return (
        str(reply or ""),
        buffer.getvalue().strip()
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(
            "[HTTP] "
            + (fmt % args)
        )

    def cors_headers(self):
        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

    def send_json(
        self,
        payload,
        status=200
    ):
        body = json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(
            status
        )
        self.cors_headers()

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header(
            "Cache-Control",
            "no-store"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    def do_OPTIONS(self):
        self.send_response(
            204
        )
        self.cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self.send_json({
                "service": "V.O.I.C.E.",
                "status": "online",
                "version": "research-v3",
                "endpoints": [
                    "GET /health",
                    "POST /chat"
                ]
            })
            return

        if self.path == "/health":
            self.send_json({
                "ok": True,
                "service": "V.O.I.C.E.",
                "brain": "online",
                "version": "research-v3"
            })
            return

        self.send_json(
            {"error": "Not found"},
            404
        )

    def do_POST(self):
        if self.path != "/chat":
            self.send_json(
                {"error": "Not found"},
                404
            )
            return

        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            if length <= 0:
                raise ValueError(
                    "Request body is empty."
                )

            if length > 100_000:
                raise ValueError(
                    "Request body is too large."
                )

            data = json.loads(
                self.rfile.read(
                    length
                ).decode("utf-8")
            )

            message = data.get(
                "message"
            )

            if not isinstance(
                message,
                str
            ):
                raise ValueError(
                    "'message' must be a string."
                )

            message = message.strip()

            if not message:
                raise ValueError(
                    "Message cannot be empty."
                )

            if len(message) > 10_000:
                raise ValueError(
                    "Message is too long."
                )

            reply, research = run_brain(
                message
            )

            self.send_json({
                "reply": reply,
                "research": research
            })

        except json.JSONDecodeError:
            self.send_json(
                {"error": "Invalid JSON."},
                400
            )

        except Exception as exc:
            traceback.print_exc()

            self.send_json(
                {"error": str(exc)},
                500
            )


def main():
    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler
    )

    print(
        "V . O . I . C . E ."
    )
    print(
        "Python backend ........ ONLINE"
    )
    print(
        f"Listening ............. http://{HOST}:{PORT}"
    )
    print(
        "GET  /health"
    )
    print(
        "POST /chat"
    )
    print()

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print(
            "\nShutting down..."
        )

    finally:
        server.server_close()


if __name__ == "__main__":
    main()
