# iPhone Live Location Display

Show the **area you're currently in** — read from your iPhone's GPS — in big
letters on a spare monitor. Your phone sends its location using a built-in
**Shortcut**, a tiny program on your computer turns the coordinates into a
place name (like *Syracuse University* or *Downtown Syracuse*), and a
fullscreen web page displays it.

- No app to install on your phone — just the built-in Shortcuts app.
- No accounts, no database, no cloud. Everything stays on your home network.
- **Privacy-friendly:** the screen only ever shows an *area name*, never your
  exact coordinates.

---

## What you need

- A computer (Windows, Mac, or Linux) with **Python 3** installed.
  - Check by opening a terminal / PowerShell and typing `python3 --version`
    (Mac/Linux) or `py --version` (Windows). If you get a version number,
    you're set. If not, install it from [python.org](https://www.python.org/downloads/)
    and, on Windows, tick **"Add Python to PATH"** during install.
- An iPhone on the **same Wi-Fi network** as the computer.

That's it — there's nothing else to download.

---

## Step 1 — Start the server on your computer

1. Download this project (green **Code** button → **Download ZIP**) and unzip
   it, or clone it with git.
2. Open a terminal / PowerShell **in that folder** and run:

   ```bash
   python3 server.py      # Mac / Linux
   py server.py           # Windows
   ```

3. You'll see something like:

   ```text
   Location server running on http://0.0.0.0:3000/
   ```

   Leave this window open — it's your server. (To stop it later, press
   `Ctrl + C`.)

---

## Step 2 — Find your computer's IP address

Your iPhone needs your computer's address on the local network. It looks like
`192.168.1.42`.

- **Windows:** open PowerShell and run `ipconfig`. Look for **IPv4 Address**
  under your Wi-Fi adapter.
- **Mac:** run `ipconfig getifaddr en0` (or check System Settings → Wi-Fi →
  Details).
- **Linux:** run `hostname -I` and use the first address.

Write this number down — you'll need it in the next step. (It usually starts
with `192.168` or `10.`)

---

## Step 3 — Build the iPhone Shortcut

This is the part that sends your location. You'll build it once in the
**Shortcuts** app (already on every iPhone).

1. Open **Shortcuts** → tap **+** (top right) to create a new shortcut.
2. Tap **Add Action** and add these actions **in order**. Search for each one
   by name in the search bar:

   | # | Action | What to set |
   |---|--------|-------------|
   | 1 | **Get Current Location** | *(nothing to change)* |
   | 2 | **Get Details of Location** | choose **Latitude**, with input = *Current Location* |
   | 3 | **Get Details of Location** | choose **Longitude**, with input = *Current Location* |
   | 4 | **Get Contents of URL** | see below ⬇️ |

3. Tap on the **Get Contents of URL** action and set it up:
   - **URL:** `http://YOUR_COMPUTER_IP:3000/location`
     (replace `YOUR_COMPUTER_IP` with the number from Step 2 — for example
     `http://192.168.1.42:3000/location`)
   - Tap **Show More**, then set **Method** to **POST**.
   - Set **Request Body** to **JSON**.
   - Add two fields (tap **Add new field** → **Text** for each, then change
     the type to **Number**):

     | Key | Value |
     |------|-------|
     | `latitude`  | the **Latitude** from action 2 |
     | `longitude` | the **Longitude** from action 3 |

     > Tip: tap the value box and pick the blue **Latitude** / **Longitude**
     > variables that appeared from the earlier actions.

4. Give the shortcut a name (e.g. **Send My Location**) and tap **Done**.
5. **Test it:** tap the shortcut to run it. The first time, your iPhone will
   ask for permission to use your location — tap **Allow**.

---

## Step 4 — Open the display

On the computer, open a web browser and go to:

```text
http://127.0.0.1:3000/
```

- Before your first location arrives it says **Waiting for location…**
- Run the shortcut on your phone → within a second or two the screen shows
  your area.
- Press **F11** (or click the ⛶ button, top-right) for a clean fullscreen view.

🎉 That's the whole thing working.

---

## Making it update automatically (optional)

iPhones **can't** run a shortcut every few seconds in the background — that's
an Apple limitation, not something this project can change. Instead, you can
trigger the shortcut automatically at sensible moments:

1. In **Shortcuts**, go to the **Automation** tab → **+** → **Create Personal
   Automation**.
2. Pick a trigger, for example:
   - **Time of Day** — e.g. every hour.
   - **When I open an app** — updates whenever you open a chosen app.
   - **Focus** — when you turn Work/Personal Focus on or off.
3. For the action, choose **Run Shortcut** and select your **Send My Location**
   shortcut.
4. Turn **off** "Ask Before Running" so it runs silently.

Each time it fires, the display refreshes. For a truly live feed you'd just
run the shortcut manually whenever you want to update it.

---

## Keep the server running in the background (Windows only, optional)

Normally the server only runs while its terminal window is open. On Windows you
can make it run quietly in the background and start automatically when you log
in:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
```

This sets up a Scheduled Task that:
- runs the server with no visible window,
- restarts it automatically if it ever stops,
- starts it every time you log in.

Then just open `http://127.0.0.1:3000/` in your browser (tip: use your
browser's "open as window / kiosk" option on a spare monitor).

To remove it later:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall-windows.ps1
```

---

## Troubleshooting

- **Shortcut says it couldn't connect / load the URL.**
  - Make sure the server terminal is still open and running.
  - Double-check the IP address in the shortcut matches Step 2, and that the
    port `:3000` is included.
  - Confirm the iPhone and computer are on the **same Wi-Fi**.
  - Your computer's firewall may be blocking incoming connections — allow
    Python through it (Windows will usually pop up asking the first time).
- **Screen stays on "Waiting for location…".** Run the shortcut on your phone
  at least once, and make sure you tapped **Allow** for location access.
- **Screen shows "Finding area…".** It received your location but couldn't look
  up a name yet (usually a brief internet hiccup). It clears on the next update.

---

## For the curious — how it works

```text
iPhone  ──(HTTP POST /location)──▶  Python server  ──(reverse geocode)──▶  Browser
  GPS coordinates                 keeps only the latest fix            fullscreen area name
                                  in memory; resolves to a place
```

- The server (`server.py`) is plain Python — no frameworks, no database. It
  stores just the most recent location in memory (a restart forgets it).
- It turns coordinates into a place name using the free
  [OpenStreetMap Nominatim](https://nominatim.org/) service, and only calls it
  when your position actually changes.
- The page (`index.html`) asks the server for the latest area once a second and
  updates the text — coordinates are never sent to the browser.

### The two endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/location` | Phone sends `{ "latitude": …, "longitude": … }` |
| `GET`  | `/latest`   | Page reads `{ "area": "Syracuse University", "timestamp": … }` |

### A note on safety

This is designed for a **trusted home network** and has no password or
encryption. Anyone on your network who knows the address could send a location
or view the current area, so don't expose port `3000` to the public internet.

---

## License

MIT — see [LICENSE](LICENSE).
