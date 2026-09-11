# Macleen's Digital — Lifetime Ownership / My Apps Update

Incremental update for the latest Macleen's project.

## What changes
- Adds **Digital → My Apps** as the customer's permanent return page for paid Lifetime hosted apps.
- Paid Lifetime apps show **Owned · Lifetime** in the Digital catalog instead of being offered for sale again.
- Opening the product detail page also blocks duplicate checkout and shows **Open App** instead.
- A paid Lifetime private order page automatically remembers the entitlement on that browser for 5 years.
- If the purchase was made while logged in, ownership follows the customer's Rewards account across devices.
- Guest Lifetime buyers can choose **Save Lifetime Access to My Account**. If they are not logged in, Macleen's sends them through login and automatically links the Lifetime order after successful login.
- The original private order page remains usable as a backup recovery link.
- No database migration/reset is required.

## Replace
Extract this ZIP over the existing project and choose **Replace files in destination**.

Affected files only:
- `app.py`
- `templates/digital/base.html`
- `templates/digital/index.html`
- `templates/digital/item.html`
- `templates/digital/order_status.html`
- `templates/digital/my_apps.html` (new)

## Deploy
```bash
git status
git add .
git commit -m "Add My Digital Apps and lifetime ownership recovery"
git push origin main
```

## Important
For a guest purchase, the browser-memory entitlement depends on the signed Macleen's cookie. If the buyer clears browser/site data or changes device before saving the Lifetime purchase to a customer account, they should use the original private order link to recover it and save it to their account.
