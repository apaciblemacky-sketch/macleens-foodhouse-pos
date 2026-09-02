# Social Share Thumbnail Header Update

- Food House page shares now declare a branded 1200x630 header preview via Open Graph / Twitter metadata.
- Craft Shop page shares now declare a branded 1200x630 header preview instead of allowing Facebook to guess the first product image.
- Individual Food and Craft product shares still prefer the product's own public image; if an image is not publicly crawlable, they fall back to the branded header preview.
- New static assets: `static/social/foodhouse-share-header.png` and `static/social/craft-share-header.png`.
- Facebook may cache old previews. After deploy, use Facebook Sharing Debugger and choose **Scrape Again** for the page URL if the old first-product thumbnail is still cached.
