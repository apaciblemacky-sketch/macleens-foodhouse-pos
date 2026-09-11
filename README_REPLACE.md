# Macleen's Hosted App — Real Install App Fix

Incremental update on top of **Macleens_Auto_Separate_PWA_Per_Hosted_App_Update.zip**.

## Why Chrome showed Bookmark / Create shortcut
The hosted app viewer could be opened on `/digital/apps/hosted/...`, while that individual app's service worker is scoped to `/digital/apps/pwa/<app-id>/`. Chromium may therefore treat the visible page as a normal webpage instead of the app's installable scope.

## Fix
All uploaded Hosted HTML Apps now enter through their dedicated PWA scope before rendering:

`/digital/apps/pwa/<app-id>/<access-mode>/<access-key>`

This keeps the current document, manifest, start URL, and service worker under the same app identity/scope, allowing Chromium to offer **Install app** instead of only Bookmark/Create shortcut when the browser supports installation.

Access protection remains unchanged for Free, Per Use, Lifetime, and Admin Free access.

## Replace
- `app.py`

No database reset required.
