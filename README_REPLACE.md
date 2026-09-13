# Macleen's Digital Accounts + PWA + CHAT Lite cumulative update v41.1

This package is cumulative over the v40 Digital 1-Day Trial + Gemini build and already includes the latest CHAT Lite PWA/video/image-preview hotfix.

## Main changes
1. Separate Digital-only customer accounts/database bind.
2. Existing Macleen's customers can use their existing account credentials in Digital.
3. Sign-in/registration required before starting a trial, opening a free hosted app, or purchasing Digital products.
4. Digital-only accounts do not gain Rewards portal access. Crafts remains guest-friendly.
5. My Apps is the Digital customer's paid Hosted App library.
6. Free Trial Users by App reporting in Digital Admin.
7. Digital catalog Open Graph/social thumbnail uses the visual face of the Digital storefront.
8. Food Storefront + Digital mobile install prompts.
9. CHAT Lite latest PWA camera/video handling, conditional Screen Share, and image attachment previews.
10. Existing 24-hour trials and server-side Gemini bridge remain included.

## Replace
Extract this ZIP into the existing Macleen's project folder and choose **Replace files in destination**.
Do not delete/reset the database.

## Render / database note
If you use SQLite on Render, keep `/opt/render/project/src/instance` on persistent storage. The Digital-only SQLite database is `instance/digital_customers.db` unless `DIGITAL_DATABASE_URL` is configured.

## Deploy
Recommended: run `DEPLOY_TO_RENDER.bat`.

Manual Git:
```
git status
git add .
git commit -m "Add Digital accounts, app install prompts, trial reporting, and CHAT Lite fixes"
git push origin main
```

Expected `/healthz` release after deployment:
`2026.09.13-digital-accounts-chatlite-v41.1`

## Validation completed before packaging
- `python -m py_compile app.py`
- `scripts/predeploy_check.py`
- v39 business/finance/analytics smoke check
- v40 Digital trial/Gemini smoke check
- v41.1 Digital accounts/PWA/CHAT Lite smoke check
- Jinja syntax parse of changed templates
- JavaScript syntax check of `static/portal-pwa-install.js`

The full Flask runtime import was not executed in the build container because Flask is not installed there; your included deployment BAT runs project checks in your own environment before push.
