# Macleen's Digital — Automatic Separate PWA Per Uploaded HTML App

This is an incremental update for the current Macleen's project.

## Replace these files
- `app.py`
- `templates/digital/admin.html`
- `templates/digital/apps/hosted_app_viewer.html`

Do not delete the database, `.env`, uploads, or unrelated project files.

## What changes
Every HTML/ZIP app uploaded through **Digital Admin → Hosted HTML Apps** can now automatically become its own independently installable web app/PWA.

Each uploaded app gets:
- a stable app identity based on its Digital product id
- its own PWA scope under `/digital/apps/pwa/<product-id>/`
- its own manifest
- its own generated icon/initials
- its own app name / short name
- its own theme color
- its own display mode (`standalone`, `fullscreen`, or `minimal-ui`)
- a customer **Install <App Name>** button after valid access
- Admin Free launch/install support

## Access remains protected
- **FREE**: can be opened/installed without payment.
- **PER USE**: still requires an active paid usage pass. Installation does not bypass expiry.
- **LIFETIME**: the owner can reopen/install indefinitely through existing Lifetime ownership/My Apps rules.
- **ADMIN**: authenticated Macleen's Admin can launch/install for free.

The service worker deliberately does not cache the protected uploaded source package, so a paid app does not become a downloadable/offline source copy.

## Admin settings
When uploading or editing a Hosted HTML App you can now set:
- `Automatically make this uploaded app independently installable` (ON by default for new uploads)
- Installed app short name
- Theme color
- Display mode

Turning installability off hides the PWA install option for that app without removing the hosted product itself.

## Future workflow
After deploying this platform update once, a new compatible `.html` or `.zip` upload can create its own web app without another Git/Render deployment.

## Deploy
```bash
git status
git add .
git commit -m "Add automatic separate PWA for every hosted HTML app"
git push origin main
```

No database reset is required. The startup compatibility migration adds the new PWA settings columns to `digital_item`.
