# Dash 1

A privacy-first desktop dashboard for a secondary display. Showcases time, weather, and upcoming Outlook calendar events from a local web server.

### Features

- **Agenda** : today's upcoming events, rolling into the next days.
- **Click to join** : events with a Teams/Zoom/Meet link open directly from dashboard.

<img width="2724" height="1563" alt="dashboard1" src="https://github.com/user-attachments/assets/3cd4ac98-7993-411a-8c05-2fd212a97dfd" />

## Setup

1. Start the server from this folder:

   ```bash
   python3 server.py      # Mac/Linux
   py server.py           # Windows
   ```

2. Open the dashboard in your browser:

   ```text
   http://127.0.0.1:5173/
   ```

3. Click the ✎ (edit) button in the top-right. The settings panel walks you
   through connecting your Outlook calendar, and also lets you
   set your city and pick a background.

Press `F11` (or the fullscreen button, top-right) for a clean display.

<img width="2717" height="1563" alt="dashboard2" src="https://github.com/user-attachments/assets/a0fc785b-f6c8-413a-a264-0f8b8c1d3113" />


## Run it in the background (Optional - for Windows only)

So the dashboard keeps running after you close the terminal and starts itself
when you log in:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
```

This registers a Scheduled Task that runs the server windowlessly with
`pythonw`, restarts it if it ever stops, and launches it at every log on.
Then make a browser shortcut to `http://127.0.0.1:5173/` (or open it with
`--kiosk` for a dedicated display).

To remove it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall-windows.ps1
```

## Notes

- Use Windows PowerToys to lock this tab on your secondary display
- Your settings are saved privately to `config.json`.
- Outlook regenerates published calendar feeds on its own schedule, so a
  brand-new event can take a while to appear.
- If nothing shows up, check `http://127.0.0.1:5173/api/events` to see the raw
  data or error.
