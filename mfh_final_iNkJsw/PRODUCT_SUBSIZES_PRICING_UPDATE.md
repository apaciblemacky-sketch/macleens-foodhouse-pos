# Product Sub-sizes + Per-size Pricing Update

This update extends Food House product sub-options with an optional **Priced Sizes** definition.

## Admin syntax

Use the new **Priced Sizes** field when adding a product or in the Bulk Catalog Editor:

`Small=35|Medium=45|Large=55`

or:

`12oz=50|16oz=65|22oz=80`

The size picker is required when sizes are configured. The selected size price is server-validated and becomes the Order Item selling price. Normal sauce/flavor sub-options still work at the same time.

Examples:

- `Priced Sizes`: `12oz=50|16oz=65|22oz=80`
- `Choices / Sub-options`: `Flavor: Wintermelon|Okinawa|Classic; Add-ons[]: Pearls|Nata`

Customers, the Tablet kiosk, Cashier POS, reservations, and collection entries all use the same server-side validation. Cart totals update to the selected size price before checkout.

The existing base product Price remains as a fallback/default catalog value. When a product has priced sizes, a valid size choice is required and the server ignores client-side attempts to alter the configured size price.
