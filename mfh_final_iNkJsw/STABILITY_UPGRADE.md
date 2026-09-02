# Macleen's Food House — Stability Upgrade

This project has been hardened for safer Render deployment and day-to-day cashier operation while preserving the owner's accounting rule that **Vault Drops count as sales**.

## What changed

- Database setup now performs explicit, logged, idempotent additive schema checks at startup instead of silently swallowing migration errors.
- Render can use `/healthz` as a database-aware health check.
- Existing staff PINs are no longer reset on every restart/deploy.
- Staff sessions expire after 8 hours of inactivity; customer sessions may persist up to 30 days.
- Production sessions use secure cookie settings and the Flask secret comes from `SECRET_KEY` when configured.
- Cashier/database query failures are logged and surfaced rather than displayed as a false empty queue.
- Storefront, tablet, direct POS, reservation, and product-based collection flows use centralized server-side quantity, availability, stock, price, and cost validation.
- Negative/zero quantities, overselling, inactive products, and browser-supplied prices are rejected server-side.
- Product cost is editable in Admin and is snapshotted into each new `OrderItem` so future COGS/gross-profit reporting uses the cost at the time of sale.
- Promo price and promo cost are editable and promo sales snapshot the configured promo cost.
- Customer card numbers are generated sequentially/uniquely instead of randomly from only 100 possible values.
- Customer card status and expiry are enforced; Admin can renew a card for one year.
- Tablet member identification now requires the real 4-digit customer PIN and verifies its password hash.
- The later portal-simplification update removes the public VIP leaderboard entirely.
- Credit eligibility and available credit limit are enforced for credit orders/registered-member collections.
- Philippine business-day calculations use `Asia/Manila`; stored timestamps remain UTC-compatible.
- Admin now separates "Set credit limit" from "Enable/Disable credit" so changing a limit no longer toggles eligibility accidentally.
- Admin can securely reset staff PINs without resetting them at application startup.

## Deliberately preserved behavior

Vault Drops remain included in gross sales. The finance calculation intentionally keeps:

```python
total_rev = order_rev + vault_drop_sales
```

When part of a Vault Drop is allocated to a product/customer, the drop balance is reduced and a completed order is created, preserving the total while adding product/customer attribution.

## Historical cost note

Old transactions retain the `cost_price` that was actually stored when they were created. If an older order stored zero cost, this upgrade does **not** rewrite history using today's product cost. New product-linked transactions snapshot current product cost automatically.

## Render / production checklist

1. Keep `DATABASE_URL` connected to the intended production PostgreSQL database.
2. Ensure `SECRET_KEY` exists in Render. `render.yaml` can generate it for a Blueprint deployment.
3. Existing `admin` and `cashier1` accounts keep their current PIN hashes. Change/reset staff PINs from the new **Staff Security** section in Admin when needed.
4. For a completely fresh database, optional environment variables `DEFAULT_ADMIN_PIN` and `DEFAULT_CASHIER_PIN` can be supplied before first boot. If omitted, the first-run local defaults are created once and a warning is logged; they are never reset on later restarts.
5. Run `python scripts/predeploy_check.py` before committing/deploying.
6. Watch Render logs on the first upgraded deploy. A real schema/database problem is now intended to fail visibly instead of silently making Cashier appear empty.

## PWA/fallback logo

The canonical ZIP referenced `/static/logo.png` but did not include it. A square `static/logo.png` has now been created from the Macleen's Food House logo already present in the uploaded Food House artwork, so the manifest and fallback image paths no longer point to a missing file.

## Cashier Specific Amounts
- Admin can enable **Specific Amt** per product and set that product's **Minimum Order Amount**.
- In Cashier POS, enabled products open an amount entry box before being added to the cart.
- Cashier may enter any amount at or above the configured minimum; the regular product price remains the default.
- The backend re-checks the minimum and ignores/rejects unauthorized custom pricing, so browser-side edits cannot bypass the rule.
- Public storefront and tablet ordering continue to use the regular product price.

