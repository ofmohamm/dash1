# iPhone Live Location Display

Show the area you are currently in, read from your iPhone's GPS, in big letters
on a monitor. Your phone sends its location with a built-in **Shortcut**, and a
fullscreen web page displays it with a bit of personality.

Runs on a free web host over HTTPS, so it works from anywhere, including cellular.
Privacy-friendly: the screen shows a place name, not a live map.

## 1. Deploy the server (Render, free)

1. Put this repo on your own GitHub (public or private both work).
2. In [Render](https://render.com): **New +** then **Blueprint**, and pick this
   repo. Render reads the included `render.yaml` and creates a free web service.
3. When asked for **SECRET**, paste a long random token (see
   [Secret token](#secret-token) below to generate one). Keep a copy.
4. Click **Apply / Create**. After a minute Render gives you an HTTPS address
   like `https://your-service.onrender.com`. This is your **server URL**.

## 2. Build the iPhone Shortcut

In the **Shortcuts** app, tap **+** and add these actions:

1. **Get Current Location**
2. **Text** action, and insert the **Current Location** variable into it. A
   location placed in a Text action turns into its full street address. (Putting
   the location straight into the JSON field below does not reliably become text,
   so it fails or sends coordinates. This Text step is what makes it work.)
3. **Get Contents of URL**
   - **URL:** your server URL followed by `/location`, for example
     `https://your-service.onrender.com/location`
   - Tap **Show More**, set **Method** to **POST**.
   - Under **Headers**, add one: key `X-Token`, value your secret from step 1.
   - Set **Request Body** to **JSON** and add one **Text** field:
     - key `area`, value the **Text** from step 2.

Name it (for example **Send My Location**), tap **Done**, run it once, and tap
**Allow** for location access.

> If the address looks wrong or shows coordinates, swap step 2 for a **Get
> Details of Location** action set to **Name** (input = *Current Location*), and
> send that as `area` instead. That gives a shorter label like the street or
> place name.

## 3. Open the display

On the display computer, open your server URL with the token on the end:

```text
https://your-service.onrender.com/?token=YOUR_SECRET
```

The first time it asks for a name, then shows something like *Omar is eating ice
cream at 123 Main St, Liverpool, NY*. Press **F11** for fullscreen. Change the
name with the person button (top right), or add `&name=Omar` to the address.

## 4. Update automatically when you start driving

iOS can run the Shortcut on its own when **Driving** Focus turns on. This works
in the background with the phone locked, and iOS can turn Driving on for you when
you start driving or connect to the car.

1. In **Shortcuts**, open the **Automation** tab, tap **+**, then **Create
   Personal Automation**.
2. Choose **Focus**, then **Driving**, then **Is Turned On**.
3. Set the action to **Run Shortcut** and pick **Send My Location**.
4. Turn **off** "Ask Before Running".

Add a second automation with **Is Turned Off** to also update where you park.
Each automation posts once, at the moment Driving turns on or off.

## Secret token

The `SECRET` you set on the host is what keeps your location private. Send it as
the `X-Token` header in the Shortcut, and as `?token=` in the display URL.

Generate a strong one with the
[1Password password generator](https://1password.com/password-generator/) (30 or
more random characters). Keep it private, and if it ever leaks, change it in the
host's settings.

## Troubleshooting

- **Shortcut cannot connect:** check the URL ends in `/location` and the Render
  service shows **Live** in the dashboard.
- **Display shows "Locked":** the `?token=` value in the address is missing or
  wrong. Open the page again with the correct token.
- **Display stays on "Looking for...":** run the Shortcut once and make sure you
  tapped **Allow**. On the free host, the server may have slept; the next update
  wakes it.

## License

MIT, see [LICENSE](LICENSE).
