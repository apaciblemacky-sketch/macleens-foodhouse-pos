# QR PH, Crafts, and installed-app updates

## Before going live

Set these Render environment variables:

- `PAYMONGO_SECRET_KEY` — enables QR PH checkout for Food Store, Digital, Crafts, and optional support contributions.
- `PUBLIC_BASE_URL` — the public HTTPS address used by payment return links.
- `WEBPUSH_VAPID_PUBLIC_KEY`, `WEBPUSH_VAPID_PRIVATE_KEY`, and `WEBPUSH_VAPID_SUBJECT` — enables installed-app notifications.

In PayMongo, configure `checkout_session.payment.paid` to call:

`https://YOUR-DOMAIN/api/paymongo/webhook`

## Sending a customer update

1. In Master Admin, Digital Admin, or Crafts Admin, open **Send installed-app update**.
2. Enter a title, short message, and the page that should open when tapped.
3. Select **Send app notification**.

Only customers who have installed/allowed notifications and selected the relevant notification category receive the update. The app requests the device's normal notification sound for new-item/adjustment alerts; silent mode, Do Not Disturb, and browser policies can still mute it.

## Monthly support

The support page offers a one-time contribution or a **monthly support pledge**. QR PH requires each payment to be approved in the customer's own payment app, so this is intentionally a manual monthly renewal—not an automatic recurring debit and no payment credential is stored.
