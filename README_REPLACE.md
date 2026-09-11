# Macleen's QR PH Fast Return Confirmation Update

Incremental update for the latest Macleen's package.

## Changes
- Back to Merchant now performs several immediate server-to-server PayMongo checks during the short propagation window.
- The private Digital order page starts checking immediately instead of waiting 5 seconds.
- It checks about every 1.2 seconds at first, then backs off automatically.
- A browser return alone still never unlocks an unpaid product; PayMongo confirmation is required.
- Old "contact Macleen's Digital on Facebook" payment copy is replaced with the current Chat with us wording.

## PayMongo setup for fastest confirmation
Register this webhook once in PayMongo Dashboard -> Developer Tools -> Webhooks:

`https://macleens-foodhouse-pos.onrender.com/api/paymongo/webhook`

Subscribe to:

`checkout_session.payment.paid`

The existing server can also recover by polling if the webhook is delayed or unavailable.

## Install
Extract this ZIP over the existing Macleen's project and replace files in destination, then deploy.
