# Original Product Photo Link Previews

Every Food House product page now provides Facebook and other social networks
with a dedicated 1200 x 630 JPEG link-preview image.

The preview:

- preserves the complete original product photo without a color filter,
  dark overlay, recoloring, or cropping;
- places the untouched photo on a clean white panel with product information
  on a separate bright panel;
- includes the product name, category, current starting price, Macleen's Food
  House branding, and a clear View & Order call to action;
- remains clear when an old product image fails by drawing a category-aware
  food or drink fallback rather than returning an empty frame;
- changes its share URL when the product name, price, size prices, photo, or
  active status changes, reducing stale Facebook preview caching;
- serves a standard progressive JPEG with an explicit content type and length;
  and
- caches generated previews so Facebook receives repeat requests quickly.

Paste or share the product link itself on Facebook. Facebook will scrape the
page metadata and make the preview image clickable, leading customers to that
exact product page. Uploading only the JPEG as a normal Facebook photo does not
make the entire photo link to the product, so use the system's Share button or
paste the product URL into the Facebook post.

Facebook can retain a previously scraped preview. When necessary, use Meta's
Sharing Debugger to scrape the product URL again after a deployment or product
photo change.
