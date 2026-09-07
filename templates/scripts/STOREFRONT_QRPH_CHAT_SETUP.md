# Storefront QR Ph, COD, and Live Chat Setup

## Replace and run

Copy this patch's folders and files into the root of the existing Macleen's Food House project, replacing files with the same name. Then double-click `RUN_MACLEENS.bat` to test locally, or double-click `DEPLOY_TO_RENDER.bat` to run checks, push GitHub, and let Render deploy.

## Turn on GCash QR Ph

1. In Render, add `PAYMONGO_SECRET_KEY` as an environment variable. Use the **Live secret key** for real payments; never put it in the source code, browser, or public key field.
2. Optional but recommended: set `PUBLIC_BASE_URL` to `https://macleens-foodhouse-pos.onrender.com`.
3. In PayMongo, make sure QR Ph is enabled for the live account. If PayMongo says “No payment methods are available,” this is an account/payment-method activation issue in PayMongo, not a storefront issue.
4. Add the PayMongo webhook endpoint:
   `https://macleens-foodhouse-pos.onrender.com/api/paymongo/webhook`
5. Open **Admin → Storefront GCash QR Ph** and select **PayMongo QR Ph**. The page refuses to enable it unless the secret is present.

Customers selecting GCash are sent to PayMongo's secure QR Ph checkout. The system only marks the payment verified after checking PayMongo from the server; a browser return or a manually typed “paid” message cannot unlock it.

## Cash on Delivery and delivery details

- In **Admin → Registered Customer Management**, use **Toggle COD** to enable Cash on Delivery for a specific customer.
- Pickup cash stays available to every active customer. Delivery uses the label **Cash on Delivery**, never “Cash on Counter.”
- In **Admin → Delivery Zone Detail Rules**, set a zone to **zone-only handoff** only if staff already knows the exact designated handoff area. Other zones force customers to enter both Purok/street and landmark.

## Live chat retention

- Every new order sends an automatic thank-you message to the order tracker.
- Customers can reply in the order tracker or use the storefront help widget. Cashiers use **Live Chats** in the POS.
- Browser sound starts after the first click/tap because browsers do not allow automatic audio before a user interaction.
- Order chats are deleted when an order is cancelled or marked fulfilled. General storefront support chats expire after 24 hours.
