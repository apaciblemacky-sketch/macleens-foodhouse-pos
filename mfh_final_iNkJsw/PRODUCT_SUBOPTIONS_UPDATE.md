# Product Sub-options Update

This update adds configurable choices to every menu product without changing the product's selling price.

## Admin setup

In **Admin > Add Product** or **Bulk Catalog Editor**, use **Choices / Sub-options**.

### Checkbox / multiple selection

Add `[]` after the group name:

`Sauce[]: Hot|Sweet`

This displays real checkboxes, so the customer/cashier may choose **Hot**, **Sweet**, or **both Hot + Sweet**. At least one must be selected.

### Single selection

Leave the group name normal:

`Flavor: Ube|Chocolate|Vanilla`

This displays radio buttons and requires exactly one choice.

You can mix both types on one product:

`Sauce[]: Hot|Sweet; Flavor: Ube|Chocolate|Vanilla`

Other examples:

- `Toppings[]: Pearl|Nata|Coffee Jelly; Sugar: 25%|50%|75%|100%`
- `Dip[]: Cheese|Garlic Mayo|Sweet Chili`
- `Spice: Mild|Medium|Hot`

## Where it works

- Public storefront ordering
- Tablet kiosk
- Cashier POS
- Cashier reservation
- For Collection product selection

Selections are saved on the Order Item and displayed in the Cashier verification queue / printed queue slip.

## Anti-abuse / validation

The browser never decides what choices are valid. The Python backend checks the submitted choices against the options configured for that exact product. Unknown groups or values are rejected. Checkbox groups accept only configured values and require at least one valid choice.

The same product can appear more than once in a cart with different choices, for example:

- Fishball — Sauce: Hot + Sweet
- Fishball — Sauce: Sweet
- Milk Tea — Flavor: Okinawa

Stock is still validated against the combined quantity of the base product.

## Pricing

Sub-options currently do not add or subtract price. Existing Fixed Price / Specific Amount behavior remains unchanged.
