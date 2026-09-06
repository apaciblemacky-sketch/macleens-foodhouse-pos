# PayPal, loyalty card, delivery, and history update — v12

## What changed

- Digital Business now supports an optional PayPal checkout for overseas buyers.
- Food House, Crafts, Cashier, cash, and GCash remain manual cashier-confirmed. They do not redirect to PayPal.
- New eligible paid purchases earn one base point for every ₱40. Master Admin can change the future amount under **Loyalty point earning**; completed historical orders retain their saved points.
- Existing delivery zones that were exactly ₱40 become ₱30, and exact ₱80 zones become ₱65 one time during startup.
- Loyalty cards are now two 2 × 2 inch square sides: QR/logo front, profile photo/name/customer number/validity back.
- Staff can open a member’s private purchase history and reinstate an existing completed, verified order for the correct customer.

## Configure PayPal in Render

1. In your PayPal Business developer account, create a **Live** REST app when you are ready to accept real payments.
2. In Render → your service → Environment, add:

   - `PAYPAL_CLIENT_ID` = your PayPal Live client ID
   - `PAYPAL_CLIENT_SECRET` = your PayPal Live secret
   - `PAYPAL_MODE` = `live`
   - `PUBLIC_BASE_URL` = `https://macleens-foodhouse-pos.onrender.com`

3. Save the variables and deploy/restart the service.
4. Recommended: create a PayPal webhook pointing to:

   `https://macleens-foodhouse-pos.onrender.com/api/paypal/webhook`

   Subscribe to `CHECKOUT.ORDER.APPROVED` and `PAYMENT.CAPTURE.COMPLETED`, then place the webhook ID in Render as `PAYPAL_WEBHOOK_ID`.

5. Open **Digital Admin**. It will show whether PayPal is ready. Do not put any secret key into the web form, source code, GitHub, or a screenshot.

## How payment and delivery work

1. The buyer selects **PayPal — international checkout** only on a Digital product.
2. The system makes a Digital order and redirects the buyer to the official PayPal website.
3. On return/webhook, the server fetches and captures the stored PayPal order itself, checking the local order ID, PHP currency, and exact amount.
4. Only then does it mark the Digital order paid and release a protected download or service fulfillment.

The private tracking page and download access code remain separate from any product-specific app password or activation code. If you set a product’s Maximum app devices to 2 or 3, paid customers receive separate one-time activation codes—only software that calls the activation API can enforce that device limit.

## Important operating notes

- Test with `PAYPAL_MODE=sandbox` and PayPal sandbox credentials first; change both credentials and mode to `live` before accepting real payments.
- PayPal availability, currency/merchant eligibility, buyer country rules, fees, and holds are controlled by PayPal. Confirm your account can receive the currencies and countries you intend to serve.
- The “Reinstate old order” tool can only attach a record already saved in your database. It does not recreate deleted data and it never changes a completed sale amount.
- Download files are forced as downloads. HTML is not run inside the portal.
