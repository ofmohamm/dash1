# iPhone Live Location Display

Show the **area you are currently in**, read from your iPhone's GPS, in big
letters on a monitor. Your phone sends its location using a built-in
**Shortcut**, a tiny server turns the coordinates into a place name (like
*Syracuse University* or *Downtown Syracuse*), and a fullscreen web page
displays it with a bit of personality.

- No app to install on your phone. Just the built-in Shortcuts app.
- No accounts, no database.
- Works from **anywhere** over encrypted HTTPS, including when your phone is on
  cellular. Your phone and the display never need to be on the same network.
- **Privacy-friendly:** the screen only ever shows an *area name*, never your
  exact coordinates.

## How it works

Your phone (on cellular or any Wi-Fi) and the display computer both talk to one
small server that lives on a free web host. Nothing on your home network is
exposed, and the traffic is encrypted by the host's HTTPS.

```text
iPhone (anywhere)  --HTTPS-->  server on a free host  <--HTTPS--  computer (just a browser tab)
                               (remembers the latest area)
```

Because that server has a public web address, you set a **secret token** so only
you can post or read your location.

---

## Step 1: Put the code on GitHub

This repository is already set up for it. If it is not already on GitHub, push
it to a repo of your own (public or private both work). The host in the next
step deploys straight from that repo.

## Step 2: Deploy to a free host (Render)

[Render](https://render.com) can host this from your GitHub repo, all in the
browser, with automatic HTTPS.

1. Create a free Render account and connect your GitHub.
2. Click **New +** then **Blueprint**, and pick this repository. Render reads
   the included `render.yaml` file and sets everything up for you.
   - If you would rather not use the Blueprint, choose **New + Web Service**
     instead, pick this repo, and set **Start Command** to `python server.py`.
3. When asked for the **SECRET** value, paste a long random string. This is your
   token. Keep a copy of it. (A quick way to make one: use a password manager to
   generate 30 or more random characters.)
4. Click **Apply / Create**. After a minute Render gives you a public address
   like:

   ```text
   https://your-service.onrender.com
   ```

   Write this address down. This is your **server URL**.

> **Good to know:** the free plan puts the server to sleep after about 15
> minutes of no traffic and forgets the last location. When that happens the
> display shows "Waiting for location..." for around 30 seconds until your next
> phone update wakes it back up. For a personal display this is usually fine,
> and the next section shows how to avoid it. (Railway and Fly.io are similar
> free options if you prefer; any host that runs a Python web process and sets
> the `PORT` environment variable works.)

### Keeping it awake (optional)

You mostly do not need to do anything here. **While the display tab is open, it
already keeps the server awake:** the page requests `/latest` every second, and
that steady traffic resets the host's idle timer. The sleep only happens when
nothing is hitting the server, such as overnight or before you open the display.

If you want it to stay warm even when the display is closed (so there is no
30-second wake-up when you walk up to the monitor), point a free uptime pinger
at the server's health check:

1. Sign up for a free pinger such as [cron-job.org](https://cron-job.org) or
   [UptimeRobot](https://uptimerobot.com).
2. Create a monitor that requests this URL every 5 to 10 minutes:

   ```text
   https://your-service.onrender.com/healthz
   ```

   `/healthz` is a tiny endpoint that needs no token and returns `{"ok": true}`,
   so it is cheap to hit and safe to leave public.

**One tradeoff to know:** Render's free tier gives about 750 running hours per
month for your account. Keeping one service awake 24/7 uses roughly 730 of them,
which fits but leaves little room for other free services. If you only use the
display during the day, set the pinger to run only during those hours (for
example 7am to midnight) to use about half that.

> Do not try to keep it awake by having the server ping itself. Once it has gone
> to sleep it cannot ping anything, and a host generally does not count a
> service's traffic to itself. Use an outside pinger.

## Step 3: Build the iPhone Shortcut

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

   > **Important:** both **Get Details of Location** actions must take **Current
   > Location** as their input. Shortcuts often auto-fills the second one with
   > the previous action's result (the Latitude number), which causes the error
   > **"could not convert from text to location."** If you see that, tap the
   > input on each Get Details of Location action and set it back to the
   > **Current Location** variable so neither one points at the other.
   >
   > **Simpler alternative that avoids the error entirely:** delete both Get
   > Details of Location actions and, in the JSON body below, insert the
   > **Current Location** variable into each value, then tap it and pick the
   > **Latitude** or **Longitude** property directly.

3. Tap the **Get Contents of URL** action and set it up:
   - **URL:** your server URL followed by `/location`, for example
     `https://your-service.onrender.com/location`
   - Tap **Show More**, set **Method** to **POST**.
   - Under **Headers**, tap **Add new header**:
     - Key: `X-Token`
     - Value: your secret from Step 2
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

## Step 4: Open the display

On the display computer, open a browser and go to your server URL with your
token on the end, like this:

```text
https://your-service.onrender.com/?token=YOUR_SECRET
```

Replace `YOUR_SECRET` with the token from Step 2.

- The first time you open it, it asks **"What's your name?"** Enter a name and
  it is remembered on that computer. The display then narrates with it, like
  *Omar is eating ice cream at Syracuse University*, picking a new quip each time
  you move to a new place. Change the name any time with the person button (top
  right), or preset it by adding `&name=Omar` to the address.
- If it shows **Locked**, the token in the address is missing or wrong.
- Run the shortcut on your phone, and within a second or two the screen shows
  the area.
- Press **F11** (or click the fullscreen button, top right) for a clean view.

That is the whole thing working from anywhere.

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

## Troubleshooting

- **Shortcut says it could not connect or load the URL.** Check the server URL
  is exactly right and ends in `/location`, and that the Render service finished
  deploying (it shows "Live" in the dashboard).
- **Shortcut runs but the display does not change.** Confirm the token in the
  Shortcut's `X-Token` header exactly matches the SECRET you set on the host,
  and that the token in your display URL matches too.
- **Display shows "Locked".** The `?token=` value in the browser address is
  missing or wrong. Open the page again with the correct token.
- **Display stays on "Looking for..." or "Waiting".** Run the shortcut at least
  once, and make sure you tapped **Allow** for location access. On the free
  host, the server may have slept and forgotten the last fix; the next update
  brings it back.
- **Display shows "Pinning down..." for a while.** It received your location but
  could not look up a name yet, usually a brief hiccup. It clears on the next
  update.

---

## For the curious: how it works inside

```text
iPhone  --HTTPS POST /location-->  Python server  --reverse geocode-->  Browser
  GPS coordinates                  keeps only the latest fix           fullscreen area name
                                   in memory; resolves to a place
```

- The server (`server.py`) is plain Python with no frameworks and no database.
  It stores just the most recent location in memory, so a restart forgets it.
- It turns coordinates into a place name using the free
  [OpenStreetMap Nominatim](https://nominatim.org/) service, and only calls it
  when your position actually changes.
- The page (`index.html`) asks the server for the latest area once a second and
  updates the text. Coordinates are never sent to the browser.

### The endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/location` | Phone sends `{ "latitude": ..., "longitude": ... }` |
| `GET`  | `/latest`   | Page reads `{ "area": "Syracuse University", "timestamp": ... }` |
| `GET`  | `/healthz`  | Keep-alive check, returns `{ "ok": true }`, no token needed |

### The secret token

Set a `SECRET` environment variable to require a token on `/location` and
`/latest`. Send it as an `X-Token` header, a `?token=` query parameter, or a
`token` field in the JSON body. If `SECRET` is left empty the server is open,
which you would only want for a quick local test, never on a public host.

### A note on safety

Deployed to a host as described here, the server uses HTTPS (encrypted) and a
secret token, so it is fine to run on the public internet for personal use. It
is a single-person personal tool, not a hardened multi-user service. Anyone who
learns your token can post or read your area, so keep the token private and
change it (in the host's settings) if it ever leaks.

---

## License

MIT, see [LICENSE](LICENSE).
