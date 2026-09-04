# Original Photo Facebook Product Preview Fix

Release: `2026.09.04-original-photo-preview-v3`

## What changed

- Product link thumbnails are now 1200 x 630 progressive JPEGs, a reliable
  feed-friendly format with explicit image headers.
- The actual product photo is displayed with its original brightness and
  colors. It is not filtered, darkened, recolored, or cropped.
- A bright white photo panel keeps darker food and drinks easy to distinguish,
  while the product name and price stay in a separate information panel.
- If a remote product photo is broken or slow, the server draws a colorful
  food or drink illustration instead of returning an empty thumbnail.
- The image version is part of the URL path. A product name, category, price,
  size price, photo, or availability change creates a fresh preview URL.
- Generated images are cached in the running server for fast repeat requests.
- Old `.png` preview URLs redirect to the new JPEG route.

## Verify after deployment

1. Open `/healthz` and confirm `2026.09.04-original-photo-preview-v3`.
2. Open any product page, use its Share button, and copy the product link.
3. Open Meta Sharing Debugger: https://developers.facebook.com/tools/debug/
4. Paste that exact product link and choose **Debug**, then **Scrape Again**.
5. Confirm the preview shows the original photo in a bright 1200 x 630 card,
   then create a new Facebook
   post using the product link.

An already-published Facebook post can keep its old cached card. Scraping again
refreshes the URL metadata, but if Facebook does not repaint the existing post,
create a new post after the successful scrape.
