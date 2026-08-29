# Product Sub-options Update

This update adds configurable choices to every menu product without changing the product's selling price.

## Admin setup

In **Admin > Add Product** or **Bulk Catalog Editor**, use **Choices / Sub-options**.

Syntax:

`Sauce: Hot|Sweet`

Multiple groups:

`Sauce: Hot|Sweet; Flavor: Ube|Chocolate|Vanilla`

Other examples:

- `Spice: Mild|Medium|Hot`
- `Sugar: 25%|50%|75%|100%; Ice: Less|Regular|Extra`
- `Dip: Cheese|Garlic Mayo|Sweet Chili`

Each configured group requires one choice when the product is ordered.

## Where it works

- Public storefront ordering
- Tablet kiosk
- Cashier POS
- Cashier reservation
- For Collection product selection

The selected choices are saved on the Order Item and displayed in the Cashier verification queue / printed queue slip.

## Anti-abuse / validation

The browser never decides what choices are valid. The Python backend checks the submitted choices against the options configured for that exact product. Unknown groups or values are rejected.

The same product can also appear more than once in a cart with different choices, for example:

- Milk Tea — Flavor: Wintermelon, Sugar: 50%
- Milk Tea — Flavor: Okinawa, Sugar: 25%

Stock is still validated against the combined quantity of the base product.

## Pricing

Sub-options currently do not add or subtract price. Existing Fixed Price / Specific Amount behavior remains unchanged.
