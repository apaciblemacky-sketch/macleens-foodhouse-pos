# Macleen's Digital Accounts v41.1

## Customer account types
- Existing Macleen's Food House / Rewards customers can sign in to Digital with their existing mobile/card identifier and PIN.
- Customers who register directly in Macleen's Digital get a separate Digital-only account stored in the `digital_accounts` database bind. A Digital-only login does not create a Rewards session and does not grant Rewards portal access.
- Crafts stays guest-friendly; no Crafts registration was added.

## Digital app flow
- Browsing the Digital catalog is public.
- Starting a Hosted App trial, opening a free Hosted App, or purchasing a Digital product requires a Digital account.
- My Apps is the signed-in customer's Digital library for paid Hosted Apps.
- The Macleen's Digital PWA opens directly to Digital and can be installed separately from Food House and Crafts.

## Trial reporting
Digital Admin includes **Free Trial Users by App** with customer identity, start/expiry, active/expired status, Gemini-call count, and whether the customer later purchased that app.

## Separate Digital database
Set `DIGITAL_DATABASE_URL` in Render if you want a separate managed database. If omitted, Digital-only accounts use `instance/digital_customers.db`. If using SQLite on Render, the `instance` directory must be on persistent storage so both Food/Rewards and Digital account databases survive deploys.

## Social preview
The Digital catalog now publishes a 1200x630 Open Graph image generated from the Digital storefront theme/featured product, so Facebook shares can use a visual thumbnail instead of a plain link card. Facebook may need to re-scrape an already-cached URL after deployment.

## Install prompt
Food Storefront and Macleen's Digital open normally in the browser. On supported phones, a custom prompt asks whether to install the portal. Choosing Install triggers the browser's real PWA prompt when available; Samsung/iPhone users receive the browser-specific Add-to-Home-Screen instruction if a native prompt is unavailable. Choosing Not now suppresses the prompt for 7 days on that browser.

## CHAT Lite included fixes
- Better camera/microphone permission/device error handling in installed PWA/browser mode.
- Screen Share stays hidden until a video call is running, and stays hidden on browsers that do not support display capture.
- Image file attachments display an in-chat preview plus Download.
