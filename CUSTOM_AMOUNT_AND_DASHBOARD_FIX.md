# Cashier Specific Amount + Customer Dashboard Fix

## Customer dashboard
- Fixed `/portal/dashboard` server error caused by an obsolete `products=products` template argument left behind after Vote/Wishlist was removed.
- The current dashboard does not need a `products` context variable, so the invalid argument was removed.
- Added a pre-deploy guard so this exact regression is caught before deployment.

## Cashier specific amount per product
- Admin can enable **Specific Amt** for each product.
- Admin sets that product's **Min Amount**.
- Cashier sees `Specific ≥ ₱X.XX` on enabled products.
- Cashier may use the regular price or enter a specific amount.
- Both browser and backend reject any amount below the configured minimum.
- The backend ignores browser price manipulation for products that are not explicitly enabled for specific amounts.
- Public storefront and tablet ordering continue to use the normal database selling price.

## Existing policies preserved
- Vault Drops remain included in gross sales by project policy.
- Existing customer, order, rewards, product and historical engagement records are not deleted.
