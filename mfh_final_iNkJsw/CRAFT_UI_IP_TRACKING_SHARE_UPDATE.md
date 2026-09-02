# Craft UI + Per-IP Engagement + Share Update

This build keeps the integrated Food House/Craft Shop system while bringing the Craft storefront/admin visual language back in line with the former standalone Macleen's Crafts UI.

## Craft engagement
- Craft storefront unique visitors are tracked by IP.
- Product views increment only once per product per IP from this update onward.
- Craft likes are stored per product + IP with a database unique constraint; a second like from the same IP does not increase the count.
- Craft comments save their source IP for admin/moderation traceability. Existing legacy comments may have no IP because that data did not exist historically.
- Existing historical aggregate likes/views are preserved; the app cannot retroactively identify which old counts came from duplicate IPs. New counts are de-duplicated.

## Sharing
- Share Craft Shop button on /craft.
- Share button on every Craft product card and Craft detail page.
- Share Food House button on /.
- Share button on every Food House product card and product detail page.
- Uses the native Web Share API on supported phones; otherwise copies the URL to clipboard.

## Admin visibility
The public Craft Shop still has no Admin/Staff shortcut. Craft Admin remains a direct URL at /admin/craft and continues to use the main ADMIN session guard.
