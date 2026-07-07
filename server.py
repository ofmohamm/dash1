#!/usr/bin/env python3
"""iPhone Live Location Display: a tiny server.

An iPhone Shortcut POSTs its current location, as text, to /location. The server
keeps only that latest place name in memory, and a fullscreen browser page polls
/latest once a second to show where you are.

Runs on a free web host (Render, Railway, Fly, etc.) so your phone can reach it
over HTTPS from anywhere. Set a SECRET environment variable: requests to
/location and /latest must then carry that token, so only you can post or read
your location.

No database, no framework. Standard-library Python only.
"""
from __future__ import annotations

import hmac
import json
import os
import threading
import time as time_module
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Shared secret. When set (required for a public web host), a matching token must
# accompany every /location and /latest request. Read once at startup; hosts
# inject it as an environment variable.
SECRET = os.environ.get("SECRET", "").strip()

# The single in-memory location. Replaced on every POST /location; nothing is
# persisted, so a restart forgets it.
state_lock = threading.Lock()
state: dict = {"area": None, "timestamp": None}

# Field names the Shortcut may use to send the place name. First non-empty wins.
TEXT_AREA_KEYS = ("area", "location", "address", "place")


def normalize_area(value: str) -> str:
    """Tidy a place name into one line: collapse the multi-line address Apple
    produces into a comma-separated string, and cap the length."""
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return ", ".join(lines)[:120]


def extract_text_area(body: dict) -> str | None:
    """Return the place name the client sent, or None if it sent none."""
    for key in TEXT_AREA_KEYS:
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_area(value)
    return None


def update_location(body: dict) -> dict:
    """Store the incoming place name and replace the displayed location."""
    area = extract_text_area(body)
    if area is None:
        raise ValueError("Send an 'area' field with your location text.")

    timestamp = body.get("timestamp")
    if not isinstance(timestamp, (int, float)):
        timestamp = int(time_module.time())

    with state_lock:
        state.update(area=area, timestamp=int(timestamp))
        return dict(state)


def request_token(headers, query: str, body: object = None) -> str:
    """Pull the caller's token from a request, wherever they put it.

    Accepts an 'X-Token' header (what the display page and Shortcut send), a
    '?token=' query parameter, or a 'token' field in the JSON body.
    """
    header_token = headers.get("X-Token")
    if header_token:
        return header_token.strip()
    query_token = urllib.parse.parse_qs(query).get("token")
    if query_token:
        return query_token[0]
    if isinstance(body, dict) and body.get("token") is not None:
        return str(body["token"])
    return ""


def authorized(headers, query: str, body: object = None) -> bool:
    """True if the request may proceed. Always true when no SECRET is set."""
    if not SECRET:
        return True
    # Constant-time compare so a wrong token can't be guessed by timing.
    return hmac.compare_digest(request_token(headers, query, body), SECRET)


class Handler(BaseHTTPRequestHandler):
    server_version = "LocationDisplay/1.0"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/latest":
            if not authorized(self.headers, parsed.query):
                self.send_json(
                    {"error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED
                )
                return
            with state_lock:
                self.send_json(dict(state))
            return
        # The page itself carries no location data, so it's always served; its
        # JavaScript reads the token from the URL and authorizes /latest.
        if path in {"/", "/index.html"}:
            self.serve_file(ROOT / "index.html", "text/html; charset=utf-8")
            return
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/location":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")

            # Accept either JSON (e.g. {"area": "..."}) or a plain-text body
            # that is the location itself. The plain-text path avoids Shortcuts'
            # JSON builder mangling multi-line addresses.
            body: dict | None = None
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, dict):
                    body = decoded
                elif isinstance(decoded, str) and decoded.strip():
                    body = {"area": decoded}
            except (ValueError, TypeError):
                body = None

            if not authorized(self.headers, parsed.query, body):
                self.send_json(
                    {"success": False, "message": "Unauthorized."},
                    status=HTTPStatus.UNAUTHORIZED,
                )
                return

            update_location(body if body is not None else {"area": raw})
            self.send_json({"success": True})
        except Exception as error:
            self.send_json(
                {"success": False, "message": str(error)},
                status=HTTPStatus.BAD_REQUEST,
            )

    def serve_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        if os.environ.get("LOCATION_DEBUG") == "1":
            super().log_message(fmt, *args)


def main() -> None:
    # Bind to 0.0.0.0 so the phone can reach this server over whatever interface
    # the web host assigns.
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "3000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Location server running on http://{host}:{port}/")
    if SECRET:
        print("  Secret token: required (SECRET is set)")
    else:
        print("  Secret token: not set (open access)")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
