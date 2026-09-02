# Craft Shop Live Catalog Import + Link-Only Admin Update

This update uses the public catalog currently visible at `https://macleens-crafts.onrender.com/` to seed the integrated Craft Shop inside the main Macleen's Food House system.

## Automatic catalog seed

On database startup the system now idempotently seeds these source categories when missing:

- Handknitted Crochet Keychains
- Tumbler Holder

It also seeds the 11 currently visible source products when an item with the same name does not already exist. The source prices, stock/pre-order state, description text, featured/top-seller state, visible like counts, and public image URLs are preserved in the seed data.

Existing Craft Shop items are never overwritten. For matching names, only blank/default image or description/category metadata may be repaired, and engagement markers are only raised/preserved rather than reset.

The public source does not expose product COGS/cost, so newly imported products start with `cost = 0.00`. Set the real unit cost from Craft Admin so gross-profit reporting becomes accurate.

## Admin access

The public Craft Shop header no longer shows either a Staff or Craft Admin button. The Master Admin header also no longer shows a Craft Shop admin shortcut.

Craft Admin is now intentionally opened by direct URL:

`/admin/craft`

The route remains protected by the main system `@require_admin` guard. If the current browser already has an active main Admin session, it opens directly; otherwise the system redirects to the normal staff login.

## Integration behavior retained

Craft orders still mirror to the main Cashier verification queue, completed Craft sales still feed the main sales/cash-flow reporting, and Craft expenses/refunds/other income remain synchronized with the main financial records.
