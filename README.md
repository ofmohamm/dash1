# iPhone Live Location Display

A minimal, self-hosted display that shows your current area — read from your
iPhone's GPS — in large type on a spare monitor. Your phone sends its location
with a native **Shortcut**; a tiny local server reverse-geocodes it and a
fullscreen page shows where you are.

No database. No accounts. No cloud. Runs entirely on your local network.

<img width="2724" height="1563" alt="location display" src="https://github.com/user-attachments/assets/3cd4ac98-7993-411a-8c05-2fd212a97dfd" />

### How it works

```text
iPhone ──(HTTP POST /location)──▶ local Python server ──(reverse geocode)──▶ browser
   GPS coordinates                stores latest in memory                fullscreen area
```

- **Server** keeps only the latest fix in memory and resolves it to a
  human-readable area with OpenStreetMap Nominatim. Nothing is persisted.
- **Display** polls `GET /latest` once a second and updates the text in place.

## Setup

### 1. Start the server on your computer

```bash
python3 server.py      # Mac/Linux
py server.py           # Windows
```

It listens on port `3000` and binds to all interfaces so your phone can reach
it. Note this computer's LAN IP address (e.g. `192.168.1.42`):

```bash
ipconfig getifaddr en0     # Mac
hostname -I                # Linux
ipconfig                   # Windows (look for IPv4 Address)
```

### 2. Open the display

On the computer, open:

```text
http://127.0.0.1:3000/
```

Press `F11` (or the fullscreen button, top-right) for a clean display. Until
the first location arrives it shows **Waiting for location…**.

### 3. Build the iPhone Shortcut

In the **Shortcuts** app, create a shortcut with these actions:

1. **Get Current Location**
2. **Get Latitude** from *Current Location* (Get Details of Location)
3. **Get Longitude** from *Current Location*
4. **Get Contents of URL**
   - URL: `http://YOUR_COMPUTER_IP:3000/location`  ← use the IP from step 1
   - Method: **POST**
   - Request Body: **JSON**
     - `latitude` (Number) → *Latitude*
     - `longitude` (Number) → *Longitude*

Run it once manually to confirm the display updates.

> **Note on continuous updates:** iOS can't reliably run a Shortcut every few
> seconds in the background — that's a platform limitation. Trigger it manually,
> or via a Personal Automation (opening an app, a time of day, a Focus change).
> Each run refreshes the display within a second or two.

## API

| Method | Path        | Body / Response |
| ------ | ----------- | --------------- |
| `POST` | `/location` | `{ "latitude": 43.0481, "longitude": -76.1474, "timestamp": 1783441110 }` → `{ "success": true }` |
| `GET`  | `/latest`   | `{ "area": "Syracuse University", "timestamp": 1783441110 }` |

`timestamp` is optional on POST — the server stamps the arrival time if it's
omitted. For privacy, `/latest` returns only the resolved **area**, never the
raw coordinates: the phone sends coordinates, but they stay in memory on the
server and are never handed to the display. If reverse geocoding fails, the
last known area is kept (`area` is `null` only until the first successful
lookup) — coordinates are never shown as a fallback.

## Run it in the background (Optional — Windows only)

So the server keeps running after you close the terminal and starts itself
when you log in:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
```

This registers a Scheduled Task that runs the server windowlessly with
`pythonw`, restarts it if it ever stops, and launches it at every log on.

To remove it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall-windows.ps1
```

## Notes

- Intended for a **trusted local network** — there's no authentication or HTTPS.
- Reverse geocoding uses the public Nominatim service; the server only calls it
  when your position actually changes, staying within its usage policy.
- Set a custom port with the `PORT` environment variable.
- Use Windows PowerToys (or your OS) to keep the tab on a secondary display.
