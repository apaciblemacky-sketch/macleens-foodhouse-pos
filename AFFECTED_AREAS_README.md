# Macleen's — New Updates (Affected Areas Only)

This package contains only files affected by the requested update. Keep your database file and unrelated files unchanged.

## Included updates
- Public wording is **Chat with us**. A single Admin master switch opens/closes all public chat channels.
- Crafts and Digital support guest chat without customer login, using temporary guest thread tokens.
- Crafts public checkout accepts **QR PH or PayPal only**.
- Featured products are restored as interactive/autoplay slideshows on Food, Crafts, and Digital. Food Featured is above “Ulam for Today”.
- Support contributions accept QR PH or PayPal and include an **Invest** entry point to the Investor Center.
- Food, Crafts, and Digital have editable announcement boards. Craft/Digital announcements are visible on child pages too.
- Master Admin includes a 30-day line graph for Storefront, Crafts, and Digital website views.
- Main Food Admin can edit product names inline; Craft and Digital retain their existing name editing.
- CHAT Lite Ephemeral is hosted inside Macleen's Digital as a `HOSTED_APP` at **₱5 per usage**. One purchased quantity creates one usage pass.

## New database tables
`db.create_all()` creates these without replacing your existing database:
- `guest_chat_message`
- `digital_usage_pass`

## CHAT Lite ₱5 usage rule
The hosted app uses the uploaded CHAT Lite interface and room flow. It is not delivered as a downloadable HTML product. A paid Digital order receives a private launch button instead.

One usage becomes ACTIVE on first launch. When the room creator leaves/closes the active room, the paid usage is ended. Invite links are marked as guest links, so an invited participant leaving does not consume/end the host's pass. A **6-hour maximum** remains as a safety expiry for abandoned sessions.

## Payment configuration
- Crafts: QR PH requires active PayMongo QR PH configuration; PayPal requires configured PayPal credentials.
- Support: QR PH and PayPal use the same configured provider credentials.
- If a provider is not configured, that payment option is not offered.

## Website-view graph
The daily line series starts collecting `PAGE_VIEW` events after this update is deployed. Existing aggregate counters do not contain enough per-day history to reconstruct older daily lines reliably.

## Validation performed here
- `app.py` Python compilation: passed.
- 62 Jinja templates parsed: 0 syntax errors.
- `static/cashier-chat-widget.js` Node syntax check: passed.
- Unified patch reconstruction test: passed.
- Full Flask runtime smoke test was not run in this sandbox because its system Python does not have Flask installed.

## Apply
Safest method: replace only the files in this package at the same paths in your project, keep `instance/foodhouse_pos.db`, then redeploy/restart.

An exact unified diff is also provided separately as `Macleens_New_Updates_Affected_Areas.patch`.
