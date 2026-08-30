# Share Menu Facebook + Email Update

This follow-up simplifies the built-in Macleen's share menu and fixes desktop behavior.

- Removed the dedicated WhatsApp and Telegram buttons.
- Facebook opens in its own popup window while the original Food House or Craft Shop page remains in place.
- The Macleen's share dialog closes when Facebook opens, so the underlying business/product page stays visible.
- Facebook popup blocking no longer redirects the original page; the link is copied (or shown for manual copy) instead.
- Email now opens a Gmail web compose popup with the page/product title and URL prefilled, avoiding the Windows `mailto:` no-action problem when no desktop mail client is configured.
- Copy Link remains available.
- Mobile **More Apps…** remains available only when the browser supports native sharing.
- Share helper cache version is bumped to `v=4`.
