# Macleen's Hosted App Install + Logo + Per-Use Hours Update

Incremental update for the latest Macleen's hosted-app/PWA build.

## What changed

1. **Web app logo/icon upload**
   - Digital Admin > Hosted HTML Apps now accepts a PNG/JPG/WebP app logo.
   - Existing uploaded apps can replace/remove the custom logo.
   - CHAT Lite and other manually managed hosted products can also upload a web app logo from Catalog & protected assets > Edit.
   - Macleen's generates safe 192x192 and 512x512 install icons automatically.

2. **Editable per-use access duration**
   - Each hosted app now has `Per-use access duration (hours)` in Digital Admin.
   - Allowed range: 1 to 168 hours.
   - Default remains 6 hours.
   - The selected duration is applied when an UNUSED paid pass is launched. Already-active passes keep the expiry time they already received.

3. **Install Web App behavior improved**
   - Replaces the immediate browser alert with a real install-preparation state.
   - Service workers now use a network-only fetch handler: no protected source is cached, while Chromium gets a full PWA worker.
   - On first install attempt the page may reload once so the service worker can control it.
   - The button changes automatically when `beforeinstallprompt` becomes available.
   - Chrome may intentionally delay its native install prompt until the user has interacted with and viewed the page for a short time. This cannot be bypassed by site JavaScript.

## Files to replace

- `app.py`
- `templates/digital/admin.html`
- `templates/digital/apps/chat_lite.html`
- `templates/digital/apps/hosted_app_viewer.html`

No database reset is required. Two Digital Item columns are added automatically by the existing lightweight schema upgrader:
- `hosted_pwa_icon_file_id`
- `hosted_per_use_hours`

## Deploy

```bash
git status
git add .
git commit -m "Improve hosted app install logo and per-use hours"
git push origin main
```
