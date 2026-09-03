# Vivid Product Link Previews

Every Food House product page now provides Facebook and other social networks
with a dedicated 1200 x 630 PNG link-preview image.

The preview:

- keeps the full product photo visible inside a branded layout;
- applies social-preview-only color, contrast, brightness, and sharpness
  enhancement without changing the original catalog image;
- includes the product name, category, current starting price, Macleen's Food
  House branding, and a clear View & Order call to action;
- remains available when an old product image fails by using the Food House
  branded fallback; and
- changes its share URL when the product name, price, size prices, photo, or
  active status changes, reducing stale Facebook preview caching.

Paste or share the product link itself on Facebook. Facebook will scrape the
page metadata and make the preview image clickable, leading customers to that
exact product page. Uploading only the PNG as a normal Facebook photo does not
make the entire photo link to the product, so use the system's Share button or
paste the product URL into the Facebook post.

Facebook can retain a previously scraped preview. When necessary, use Meta's
Sharing Debugger to scrape the product URL again after a deployment or product
photo change.
