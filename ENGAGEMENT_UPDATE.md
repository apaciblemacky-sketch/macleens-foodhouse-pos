# Macleen's Food House — Customer Suggestion & Portal Simplification Update

This release keeps the Stability Upgrade and the existing sales/rewards/promo systems, while simplifying the customer portal around walk-in engagement.

## Implemented changes

- Admin product sorting now happens instantly in the browser without reloading the Admin page.
- Search and status filters remain selected while sorting.
- The public Top 10 VIP rewards leaderboard was removed from the storefront.
- Customer Vote & Wishlist UI was retired.
- Customers now get one simple free-text prompt:
  **“What would you like to buy from our shop?”**
- Suggestions may be past products, current products, or completely new ideas.
- Suggestions are stored with customer ID, customer name, text, timestamp and status.
- Admin has a Customer Product Requests list with:
  - search
  - status filter
  - NEW / CONSIDERING / PLANNED / AVAILABLE / ARCHIVED workflow
  - repeated-request demand badges and a top-demand summary
- Free Wi-Fi claim/top-up controls were removed from the customer and cashier interfaces.
- Wi-Fi, Vote and Wishlist routes were retired so old links cannot continue using those features.
- Historical database columns/tables for old engagement features are not destructively deleted.
- Customer portal primary actions are now:
  - My Rewards
  - Suggest a Product
  - Today's Member Deals
  - Order / View Menu
- Table QR now opens the product suggestion section.
- Wi-Fi QR was removed from the printable QR kit.
- New product suggestions do not award the old Vote/Wishlist +2 points.
- Vault Drop remains included in gross sales by project policy.

## New table

`product_suggestion`

Fields:
- id
- customer_id
- customer_name
- suggestion_text
- status
- created_at

Existing deployments create the new table automatically through `db.create_all()`.

## Pre-deploy check

Run:

```bash
python scripts/predeploy_check.py
```

The checker now verifies that:
- the product suggestion routes/model exist,
- retired Wi-Fi/Vote/Wishlist routes are absent,
- the public VIP leaderboard is absent,
- Admin sorting is client-side,
- Vault Drop remains included in gross sales.

## Cashier Specific Amounts
- Admin can enable **Specific Amt** per product and set that product's **Minimum Order Amount**.
- In Cashier POS, enabled products open an amount entry box before being added to the cart.
- Cashier may enter any amount at or above the configured minimum; the regular product price remains the default.
- The backend re-checks the minimum and ignores/rejects unauthorized custom pricing, so browser-side edits cannot bypass the rule.
- Public storefront and tablet ordering continue to use the regular product price.


## Follow-up: Cashier specific amounts + dashboard repair
- Products can now be individually configured to accept a Cashier-entered specific amount with a product-level minimum.
- Specific amounts are enforced server-side and cannot go below the configured minimum.
- Fixed the customer dashboard 500 error caused by a retired/undefined `products` context variable.
