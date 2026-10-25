# Connect your channel (about 10 minutes, once)

The pack signs in with **your own** Google Cloud OAuth client, so your channel data goes from Google straight to your
computer. Nobody else (including us) sees it. Scopes are read-only: `youtube.readonly` and `yt-analytics.readonly`.

Steps follow Google's own guides (read 2026-10-25):
https://developers.google.com/workspace/guides/configure-oauth-consent ·
https://developers.google.com/workspace/guides/create-credentials

1. Open https://console.cloud.google.com/ and create a project (any name, e.g. `my-channel-operator`).
2. **APIs & Services → Library**: enable **YouTube Data API v3**, **YouTube Analytics API** and, for thumbnail CTR,
   **YouTube Reporting API**.
3. **Google Auth platform → Branding**: click *Get started*, give the app a name and your email.
   **Audience**: choose *External*, then under *Test users* add the Google account that owns the channel.
4. **Google Auth platform → Clients → Create client → Application type: Desktop app** → Create → **Download JSON**.
   Keep this file private; do not commit it anywhere.
5. In Claude: *"connect my YouTube channel"* (or run
   `python3 scripts/yto.py connect --client ~/Downloads/client_secret_XXXX.json`). A Google page opens; sign in with
   the channel's account. Google may warn that the app is unverified — it is your own app, so continue.

## Good to know
- **7-day sign-in in Testing.** Google issues refresh tokens that expire in 7 days when the consent screen is in
  "Testing" (https://developers.google.com/identity/protocols/oauth2). Either run connect again when the pack says the
  sign-in ended, or set the app's *Audience → Publishing status* to *In production*; Google may then show an
  "unverified app" screen at sign-in — it is your own app.
- **Remote / cloud session?** Use `connect --manual`: open the printed address on any device, sign in, then paste the
  address the browser lands on (`http://127.0.0.1:8765/?code=…`, "site can't be reached" is expected).
- **Quota.** A weekly run uses about 5 of the 10,000 Data API units per day (the Analytics API has its own quota).
- **Delete everything:** `yto.py forget` removes the token, profile, snapshots and caches from
  `~/.youtube-operator`. Revoke the app at https://myaccount.google.com/permissions.
- **Windows:** use `python` or `py` instead of `python3` if `python3` is not found.
