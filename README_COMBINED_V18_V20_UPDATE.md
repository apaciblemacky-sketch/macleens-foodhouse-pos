# Macleen's Combined v18–v20 Update

This package is designed for the server version shown in your screenshots. It includes the earlier Hidden Treats, Unpaid Orders/live cashier chat, and the Android/tablet Cashier layout update.

## Install

1. Extract this ZIP into the root of your GitHub-connected Macleen's project.
2. Choose **Replace the files in the destination** when Windows asks.
3. Double-click `DEPLOY_TO_RENDER.bat`.
4. Type `DEPLOY` when it asks for confirmation. Render deploys after GitHub receives the push.

## Included changes

- The former `/tablet` ordering page and tablet checkout route are removed. Your historical orders are not changed.
- Android/tablet Cashier POS has one left-side tab panel: **Pending**, **Members**, **Credit**, **Unpaid**, **Recent**, and **Orders**.
- The menu stays in the center and the **Counter Tray stays on the far right** in Android/tablet landscape mode.
- Pending Cashier orders have **⚠ UNPAID**, which puts the order in the visible Unpaid Orders queue.
- Storefront order chat opens with a “Please standby” message and reopens when the cashier replies.
- Hidden Treat Hunts remain in **Master Control → POS Terminal**, between Product Bundle Deals and Bulk Catalog Editor.

## Quick check after Render is Live

1. Open `https://macleens-foodhouse-pos.onrender.com/healthz` and confirm release `2026.09.08-tablet-cashier-layout-v20`.
2. Open `/tablet`; it should show **Not Found**.
3. On Android/tablet Cashier POS, use the left-side tabs. Confirm Counter Tray remains on the far right.
4. Confirm a reported unpaid order appears in **Unpaid Orders**.
