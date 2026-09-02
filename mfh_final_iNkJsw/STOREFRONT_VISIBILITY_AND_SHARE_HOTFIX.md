# Storefront Visibility + Product Share Hotfix

This update fixes two public Food House storefront problems.

## 1. Product Share buttons

Food product Share buttons now use delegated click handlers and HTML data attributes instead of inline JavaScript containing a product name. This avoids broken clicks when names contain apostrophes, quotes, emoji, or other special characters.

The safe handler is used on:

- All Dishes product cards;
- Featured product cards;
- Best Seller product cards;
- individual Food House product detail pages.

If the normal Macleen's share dialog cannot load, the button still falls back to copying/showing the product link instead of doing nothing.

The share helper cache version was bumped to v6.

## 2. Active products no longer disappear because of selling hours

The public storefront now separates **visibility** from **orderability**:

- `Active = ON` means the product remains visible on the storefront.
- `Featured = ON` means it remains visible in Featured while Active.
- `Best Seller = ON` means it remains visible in Best Sellers while Active.
- optional Start/End availability times only control whether the Add-to-Basket button is enabled at the current Philippine time.

Outside the product's configured ordering window, the product stays visible but shows **Not Available to Order Now**. Server-side checkout validation still blocks orders outside the schedule.

This prevents active Featured/Best Seller products from seeming to disappear simply because their time window is currently closed.
