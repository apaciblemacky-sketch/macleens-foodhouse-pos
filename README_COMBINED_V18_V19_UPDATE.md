# Macleen's Combined v18–v19 Update

This package is designed for the server version shown in your screenshot. It includes both the previously missing **Hidden Treats** update and the new **Unpaid Orders + live cashier chat** update.

## Install

1. Extract this ZIP into the root of your GitHub-connected Macleen's project.
2. Choose **Replace files** when Windows asks.
3. Double-click `DEPLOY_TO_RENDER.bat`.
4. Type `DEPLOY` when it asks for confirmation. Render will deploy after GitHub receives the push.

## New in this update

- Pending cashier orders now have an orange **⚠ UNPAID** button. It moves the order directly to the existing **Unpaid Orders** list and places the order on payment hold.
- Settling that item from **Unpaid Orders** clears the customer balance and completes the order.
- A completed non-QR-Ph storefront order stays on the storefront and opens the order-specific **Cashier chat** immediately with the automatic “Please standby” message.
- If the customer closes that chat, a later cashier reply automatically opens it again and plays a notification sound after the browser has received a tap.
- The same live order chat is available from the customer Rewards portal.
- QR Ph orders still go to PayMongo first, because the secure payment step must happen before returning to the order tracker. The tracker already shows the same live cashier chat.
- Hidden Treat Hunts remain available in **Master Control → POS Terminal**, below **Product Bundle Deals** and above **Bulk Catalog Editor**.

## Quick check after Render says Live

1. Open `https://macleens-foodhouse-pos.onrender.com/healthz` and confirm release `2026.09.07-unpaid-livechat-v19`.
2. Create a cash storefront order. The Cashier chat should open and say “Please standby”.
3. In Cashier POS, select **⚠ UNPAID** on a pending order. It must appear in **Unpaid Orders** immediately.
4. Send a cashier reply. The customer chat should reopen and make a sound after the customer has tapped/clicked the page once.
