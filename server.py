#!/usr/bin/env python3
"""iPhone Live Location Display — a tiny local server.

An iPhone Shortcut POSTs its GPS coordinates to /location. The server keeps
only the latest fix in memory, reverse-geocodes it to a human-readable area
with OpenStreetMap Nominatim, and a fullscreen browser page polls /latest once
a second to show where you are.

No database, no auth, no framework. Standard-library Python only.
"""
from __future__ import annotations

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
    coordinates — the display shows a human-readable area only, never a precise
    position — so the client just keeps showing the last known area (or a
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
        # Don't cache a failure — a transient Nominatim hiccup shouldn't stick.
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

    # Geocode outside the lock — a slow Nominatim call shouldn't block /latest
    # readers. The store itself is swapped atomically under the lock.
    area = area_for(latitude, longitude)

    with state_lock:
        # If this fix couldn't be resolved to an area, keep the last known one
        # rather than blanking the display — POSTs are infrequent (iOS can't
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


class Handler(BaseHTTPRequestHandler):
    server_version = "LocationDisplay/1.0"

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/latest":
            # Expose only the resolved area (and when it was updated) — never
            # the raw coordinates. The display names an area, nothing precise.
            with state_lock:
                self.send_json(
                    {"area": state["area"], "timestamp": state["timestamp"]}
                )
            return
        if path in {"/", "/index.html"}:
            self.serve_file(ROOT / "index.html", "text/html; charset=utf-8")
            return
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path != "/location":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object.")
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
    # Bind to 0.0.0.0 so the iPhone on the same network can POST to this
    # machine's LAN IP. Intended for a trusted local network only.
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "3000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Location server running on http://{host}:{port}/")
    print(f"  iPhone Shortcut → POST http://<this-computer-ip>:{port}/location")
    print(f"  Display page    → open http://127.0.0.1:{port}/ on this computer")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
