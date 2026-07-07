# iPhone Live Location Display

Show the **area you are currently in**, read from your iPhone's GPS, in big
letters on a monitor. Your phone sends its location using a built-in
**Shortcut**, a tiny server turns the coordinates into a place name (like
*Syracuse University* or *Downtown Syracuse*), and a fullscreen web page
displays it.

- No app to install on your phone. Just the built-in Shortcuts app.
- No accounts, no database.
- **Privacy-friendly:** the screen only ever shows an *area name*, never your
  exact coordinates.

## Which setup do I need?

There are two ways to run this. Pick based on where your phone is.

| Your situation | Use this |
|----------------|----------|
| Phone is on **cellular / mobile data**, or the display is a computer you **cannot install software on** (like a work machine) | **Setup A: Free web host.** Works from anywhere over encrypted HTTPS. |
| Phone and computer are **always on the same home Wi-Fi** | **Setup B: Home network.** Everything stays on your local network. |

If you are unsure, use **Setup A**. It works everywhere.

Both setups run the exact same program. The only difference is where it lives
and whether you use a secret token.

---

# Setup A: Free web host (works on cellular)

Your phone on mobile data cannot reach a computer sitting on your home Wi-Fi,
and a locked-down work computer may not let you install anything. The fix is to
put the tiny server on a **free web host**. Both your phone and the display
computer then talk to one public web address over **HTTPS** (encrypted), so the
"is HTTP secure" problem goes away and nothing on your home network is exposed.

```text
iPhone (cellular)  --HTTPS-->  server on a free host  <--HTTPS--  computer (just a browser tab)
                               (remembers the latest area)
```

Because this address is on the public internet, you set a **secret token** so
only you can post or read your location.

### A1. Put the code on GitHub

This repository is already set up for it. If you have not already, push it to a
GitHub repo of your own (public or private both work).

### A2. Deploy to Render (free)

[Render](https://render.com) can host this straight from your GitHub repo, all
in the browser, with automatic HTTPS.

1. Create a free Render account and connect your GitHub.
2. Click **New +** then **Blueprint**, and pick this repository. Render reads
   the included `render.yaml` file and sets everything up for you.
   - If you would rather not use the Blueprint, choose **New + Web Service**
     instead, pick this repo, and set **Start Command** to `python server.py`.
3. When asked for the **SECRET** value, paste a long random string. This is your
   token. Keep a copy of it. (A quick way to make one: mash the keyboard, or use
   a password manager to generate 30+ random characters.)
4. Click **Apply / Create**. After a minute Render gives you a public address
   like:

   ```text
   https://your-service.onrender.com
   ```

   Write this address down. This is your **server URL**.

> **Good to know:** the free plan puts the server to sleep after about 15
> minutes of no traffic and forgets the last location. When that happens the
> display shows "Waiting for location..." for around 30 seconds until your next
> phone update wakes it back up. For a personal display this is usually fine.
> (Railway and Fly.io are similar free options if you prefer; any host that runs
> a Python web process and sets the `PORT` environment variable works.)

### A3. Build the iPhone Shortcut

This is the part that sends your location. You build it once in the
**Shortcuts** app (already on every iPhone).

1. Open **Shortcuts**, tap **+** (top right) to create a new shortcut.
2. Tap **Add Action** and add these actions **in order**. Search for each one
   by name:

   | # | Action | What to set |
   |---|--------|-------------|
   | 1 | **Get Current Location** | nothing to change |
   | 2 | **Get Details of Location** | choose **Latitude**, input = *Current Location* |
   | 3 | **Get Details of Location** | choose **Longitude**, input = *Current Location* |
   | 4 | **Get Contents of URL** | see below |

3. Tap the **Get Contents of URL** action and set it up:
   - **URL:** your server URL followed by `/location`, for example
     `https://your-service.onrender.com/location`
   - Tap **Show More**, set **Method** to **POST**.
   - Under **Headers**, tap **Add new header**:
     - Key: `X-Token`
     - Value: your secret from step A2
   - Set **Request Body** to **JSON** and add two fields (tap **Add new field**,
     choose **Number** for each):

     | Key | Value |
     |------|-------|
     | `latitude`  | the **Latitude** from action 2 |
     | `longitude` | the **Longitude** from action 3 |

     > Tip: tap the value box and pick the blue **Latitude** / **Longitude**
     > variables that came from the earlier actions.

4. Name the shortcut (for example **Send My Location**) and tap **Done**.
5. **Test it:** tap the shortcut to run it. The first time, your iPhone asks for
   permission to use your location. Tap **Allow**.

### A4. Open the display

On the display computer, open a browser and go to your server URL with your
token on the end, like this:

```text
https://your-service.onrender.com/?token=YOUR_SECRET
```

Replace `YOUR_SECRET` with the token from step A2.

- Before your first location arrives it shows **Waiting for location...**
- If it shows **Locked**, the token in the address is missing or wrong.
- Run the shortcut on your phone, and within a second or two the screen shows
  your area.
- Press **F11** (or click the button, top right) for a clean fullscreen view.

That is the whole thing working from anywhere.

---

# Setup B: Home network (same Wi-Fi)

Use this if your phone and computer are always on the same home Wi-Fi. Nothing
leaves your network and you do not need a token.

### B1. Start the server on your computer

You need **Python 3** installed. Check by opening a terminal or PowerShell:
`python3 --version` (Mac/Linux) or `py --version` (Windows). If you do not have
it, install it from [python.org](https://www.python.org/downloads/) and, on
Windows, tick **Add Python to PATH** during install.

Download this project (green **Code** button, then **Download ZIP**) and unzip
it, open a terminal in that folder, and run:

```bash
python3 server.py      # Mac / Linux
py server.py           # Windows
```

You will see `Location server running on http://0.0.0.0:3000/`. Leave this
window open. To stop it later, press `Ctrl + C`.

### B2. Find your computer's IP address

- **Windows:** run `ipconfig`, look for **IPv4 Address** under your Wi-Fi.
- **Mac:** run `ipconfig getifaddr en0`.
- **Linux:** run `hostname -I` and use the first address.

It looks like `192.168.1.42`.

### B3. Build the iPhone Shortcut

Follow the same steps as **A3** above, with two changes:

- **URL:** `http://YOUR_COMPUTER_IP:3000/location` (the IP from B2, for example
  `http://192.168.1.42:3000/location`).
- **Skip the `X-Token` header.** On your home network there is no secret to send.

### B4. Open the display

On the computer, open:

```text
http://127.0.0.1:3000/
```

Run the shortcut on your phone and your area appears.

---

## Making it update automatically (optional)

iPhones **cannot** run a shortcut every few seconds in the background. That is
an Apple limitation, not something this project can change. Instead you can
trigger the shortcut automatically at sensible moments:

1. In **Shortcuts**, open the **Automation** tab, tap **+**, then **Create
   Personal Automation**.
2. Pick a trigger, for example:
   - **Time of Day**, such as every hour.
   - **When I open an app**, to update whenever you open a chosen app.
   - **Focus**, when you turn Work or Personal Focus on or off.
3. For the action, choose **Run Shortcut** and select your **Send My Location**
   shortcut.
4. Turn **off** "Ask Before Running" so it runs quietly.

Each time it fires, the display refreshes. For a truly live view, just run the
shortcut by hand whenever you want to update it.

---

## Keep the server running in the background (Setup B, Windows only, optional)

If you are using **Setup B** on a Windows computer you own, you can make the
server run quietly in the background and start when you log in:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
```

This sets up a Scheduled Task that runs the server with no visible window,
restarts it if it ever stops, and starts it every time you log in. Then open
`http://127.0.0.1:3000/` in your browser.

To remove it later:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall-windows.ps1
```

(With **Setup A** the host keeps the server running for you, so you do not need
this.)

---

## Troubleshooting

- **Shortcut says it could not connect or load the URL.**
  - Setup A: check the server URL is exactly right and ends in `/location`, and
    that the Render service finished deploying (it shows "Live" in the
    dashboard).
  - Setup B: check the IP matches step B2, includes `:3000`, and that the phone
    and computer are on the **same Wi-Fi**. Your computer's firewall may block
    incoming connections, so allow Python through it.
- **Shortcut runs but the display does not change.** Confirm the token in the
  Shortcut's `X-Token` header exactly matches the SECRET you set on the host,
  and the token in your display URL matches too.
- **Display shows "Locked".** The `?token=` value in the browser address is
  missing or wrong. Open the page again with the correct token.
- **Display stays on "Waiting for location...".** Run the shortcut at least
  once, and make sure you tapped **Allow** for location access. On the free
  host, the server may have slept and forgotten the last fix; the next update
  brings it back.
- **Display shows "Finding area...".** It received your location but could not
  look up a name yet, usually a brief hiccup. It clears on the next update.

---

## For the curious: how it works

```text
iPhone  --HTTP POST /location-->  Python server  --reverse geocode-->  Browser
  GPS coordinates                 keeps only the latest fix           fullscreen area name
                                  in memory; resolves to a place
```

- The server (`server.py`) is plain Python with no frameworks and no database.
  It stores just the most recent location in memory, so a restart forgets it.
- It turns coordinates into a place name using the free
  [OpenStreetMap Nominatim](https://nominatim.org/) service, and only calls it
  when your position actually changes.
- The page (`index.html`) asks the server for the latest area once a second and
  updates the text. Coordinates are never sent to the browser.

### The two endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/location` | Phone sends `{ "latitude": ..., "longitude": ... }` |
| `GET`  | `/latest`   | Page reads `{ "area": "Syracuse University", "timestamp": ... }` |

### The secret token

Set a `SECRET` environment variable to require a token on both endpoints. Send
it as an `X-Token` header, a `?token=` query parameter, or a `token` field in
the JSON body. When `SECRET` is empty (Setup B on a home network), the server is
open and no token is needed.

### A note on safety

Setup A uses HTTPS (encrypted) and a secret token, so it is safe to run on the
public internet for personal use. Setup B has no encryption or password and is
meant for a **trusted home network** only. Do not expose the Setup B server
(port 3000) directly to the internet; use Setup A for remote access instead.

---

## License

MIT, see [LICENSE](LICENSE).
