#!/usr/bin/env python3
"""iPhone Live Location Display: a tiny server.

An iPhone Shortcut POSTs its GPS coordinates to /location. The server keeps
only the latest fix in memory, reverse-geocodes it to a human-readable area
with OpenStreetMap Nominatim, and a fullscreen browser page polls /latest once
a second to show where you are.

It runs fine on your home network, or on a free web host (Render, Railway, Fly,
etc.) so your phone can reach it over HTTPS from cellular. When deployed to a
public host, set a SECRET environment variable: requests to /location and
/latest must then carry that token, so only you can post or read your location.

No database, no framework. Standard-library Python only.
"""
from __future__ import annotations

import hmac
import json
import os
import threading
import time as time_module
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Optional shared secret. When empty (the default), the server is open, which is
# fine on a trusted home network. When set (required for a public web host), a
# matching token must accompany every /location and /latest request. Read once
# at startup; hosts inject it as an environment variable.
SECRET = os.environ.get("SECRET", "").strip()

# The single in-memory location. Replaced wholesale on every POST /location;
# nothing is persisted, so a restart forgets everything (spec: no persistence).
state_lock = threading.Lock()
state: dict = {
    "latitude": None,
    "longitude": None,
    "area": None,
    "timestamp": None,
}

# Nominatim's usage policy requires a descriptive User-Agent and asks for at
# most ~1 request/second. The browser polls /latest every second but we only
# geocode when the coordinates actually move, so we stay well under the limit.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
GEOCODE_USER_AGENT = "iphone-location-display/1.0 (personal local use)"

# Ignore GPS jitter: only re-geocode once you've moved a meaningful distance.
# ~0.0003 degrees is roughly 30 m, enough to name a new area without spamming.
MIN_MOVE_DEGREES = 0.0003

# Remembers the last coordinates we geocoded so repeated near-identical fixes
# reuse the cached area instead of hitting Nominatim on every poll.
_geocode_cache: dict = {"latitude": None, "longitude": None, "area": None}


def reverse_geocode(latitude: float, longitude: float) -> str | None:
    """Resolve coordinates to a short area name, or None if it can't.

    Prefers the most specific meaningful label Nominatim offers (a named
    place, then neighbourhood, suburb, city district, etc.) so the display
    reads like "Syracuse University" rather than a full postal address.
    """
    query = urllib.parse.urlencode(
        {
            "lat": f"{latitude:.6f}",
            "lon": f"{longitude:.6f}",
            "format": "jsonv2",
            "zoom": "16",
            "addressdetails": "1",
        }
    )
    req = urllib.request.Request(
        f"{NOMINATIM_URL}?{query}",
        headers={"User-Agent": GEOCODE_USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8", errors="replace"))
    except Exception:
        return None

    if data.get("name"):
        return str(data["name"])

    address = data.get("address") or {}
    for key in (
        "neighbourhood",
        "suburb",
        "quarter",
        "city_district",
        "hamlet",
        "village",
        "town",
        "city",
        "municipality",
        "county",
        "state",
    ):
        if address.get(key):
            return str(address[key])

    return data.get("display_name") or None


def area_for(latitude: float, longitude: float) -> str | None:
    """Area name for coordinates, reusing the cache for tiny movements.

    Returns None if geocoding fails. We deliberately never fall back to raw
    coordinates (the display shows a human-readable area only, never a precise
    position), so the client just keeps showing the last known area (or a
    "finding area" note) until the next lookup succeeds.
    """
    cache = _geocode_cache
    if (
        cache["area"] is not None
        and cache["latitude"] is not None
        and abs(latitude - cache["latitude"]) < MIN_MOVE_DEGREES
        and abs(longitude - cache["longitude"]) < MIN_MOVE_DEGREES
    ):
        return cache["area"]

    area = reverse_geocode(latitude, longitude)
    if area is None:
        # Don't cache a failure; a transient Nominatim hiccup shouldn't stick.
        return None

    _geocode_cache.update(latitude=latitude, longitude=longitude, area=area)
    return area


def parse_coordinate(value: object, name: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be a number.")
    if number != number:  # NaN
        raise ValueError(f"'{name}' must be a real number.")
    return number


def update_location(body: dict) -> dict:
    """Validate an incoming fix, geocode it, and replace the stored location."""
    latitude = parse_coordinate(body.get("latitude"), "latitude")
    longitude = parse_coordinate(body.get("longitude"), "longitude")
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise ValueError("Coordinates are out of range.")

    timestamp = body.get("timestamp")
    if not isinstance(timestamp, (int, float)):
        timestamp = int(time_module.time())

    # Geocode outside the lock: a slow Nominatim call shouldn't block /latest
    # readers. The store itself is swapped atomically under the lock.
    area = area_for(latitude, longitude)

    with state_lock:
        # If this fix couldn't be resolved to an area, keep the last known one
        # rather than blanking the display, since POSTs are infrequent (iOS can't
        # run the Shortcut continuously), so the old area is the best guess
        # until the next successful lookup.
        if area is None:
            area = state.get("area")
        state.update(
            latitude=latitude,
            longitude=longitude,
            area=area,
            timestamp=int(timestamp),
        )
        return dict(state)


def request_token(headers, query: str, body: object = None) -> str:
    """Pull the caller's token from a request, wherever they put it.

    Accepts an 'X-Token' header (what the display page and Shortcut send), a
    '?token=' query parameter, or a 'token' field in the JSON body, so the
    setup that's easiest in a given tool always works.
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
            # Expose only the resolved area (and when it was updated), never
            # the raw coordinates. The display names an area, nothing precise.
            with state_lock:
                self.send_json(
                    {"area": state["area"], "timestamp": state["timestamp"]}
                )
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
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object.")
            if not authorized(self.headers, parsed.query, body):
                self.send_json(
                    {"success": False, "message": "Unauthorized."},
                    status=HTTPStatus.UNAUTHORIZED,
                )
                return
            update_location(body)
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
    # Bind to 0.0.0.0 so the phone can reach this server, whether that's over
    # the LAN (home Wi-Fi) or the public interface a web host assigns.
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "3000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Location server running on http://{host}:{port}/")
    print(f"  iPhone Shortcut: POST to /location")
    print(f"  Display page:    open / in a browser")
    if SECRET:
        print("  Secret token:    required (SECRET is set)")
    else:
        print("  Secret token:    not set (open access; fine on a trusted LAN)")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
