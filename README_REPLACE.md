# Macleen's Payment Confirmation + Storefront Digital Nav Update

Incremental replacement package for the latest Macleen's build.

## What changed

1. **Fix PayMongo confirmation**
   - Checkout creation remains on PayMongo's v2 create endpoint.
   - Checkout-session verification now uses the current official retrieval endpoint:
     `GET https://api.paymongo.com/v1/checkout_sessions/{id}`.
   - The previous build used `/v2/checkout_sessions/{id}` for verification. Current PayMongo docs specify `/v1/checkout_sessions/{id}` for retrieval, which could leave completed QR PH orders stuck in PENDING.
   - The fix applies to Digital, Food Storefront, Crafts, and Support QR PH checks.
   - Existing fast polling / Back-to-Merchant confirmation behavior remains included.

2. **Macleen's Digital added to the Food Storefront mobile bottom navigation**
   - New `💻 Digital` tab appears beside the Food storefront navigation.
   - Bottom navigation was tightened so Home, Menu, Digital, Community, Rewards, and Orders/Login fit on mobile.
   - Because the storefront PWA has root scope, Digital opens from the installed Macleen's web app as well.

## Files to replace

- `app.py`
- `templates/store_catalog.html`
- `templates/digital/order_status.html`

Extract into the existing project root and replace files when prompted.

Then deploy:

```bash
git status
git add .
git commit -m "Fix PayMongo confirmation and add Digital to storefront nav"
git push origin main
```

No database reset or migration is required for this update.
