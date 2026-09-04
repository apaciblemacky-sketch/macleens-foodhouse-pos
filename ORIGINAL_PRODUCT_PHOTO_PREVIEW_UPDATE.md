# Original Product Photo Preview Update

Release: `2026.09.04-original-photo-preview-v3`

The Facebook product thumbnail keeps the exact product photo color and
brightness. The system only resizes the photo to fit inside a bright white
panel; it does not apply a food filter, dark overlay, color enhancement, or
crop. Product information remains on its own clean panel.

The reliable JPEG delivery, 1200 x 630 resolution, crawler warm-up, server
cache, versioned URLs, AI Marketing link refresh, and old-PNG redirect remain.

After deployment, use Meta Sharing Debugger and choose **Scrape Again** for the
exact product URL. The new style-version marker creates a fresh image URL so
Facebook does not keep the previous filtered thumbnail.
