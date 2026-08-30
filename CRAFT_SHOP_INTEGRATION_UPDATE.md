# Macleen's Craft Shop Integration Update

This build merges the standalone Craft Shop into the main Macleen's Food House Flask application and database.

## New active portals

- Public Craft Shop: `/craft`
- Craft Admin: `/admin/craft`
- Main Cashier remains: `/pos/cashier`
- Main Admin remains: `/admin`
- Cash Flow remains: `/admin/cash-flow`

The Craft Admin uses the same ADMIN login/session as the Food House master system. There is no second craft-admin password to maintain.

## Financial synchronization

Craft orders are immediately mirrored to the main `order` / `order_item` tables as `order_type=CRAFT` and enter the Cashier `VERIFICATION` queue. They do not count as revenue until the cashier accepts/completes them.

When the cashier accepts a Craft order:

- the main order becomes COMPLETED;
- the Craft order becomes COMPLETED/PAID;
- selling price and item cost snapshots remain attached to the transaction;
- the sale appears in the master Admin financial reports;
- the sale appears in the Cash Flow actual-sales history and therefore participates in the selected actual-sales average;
- if the contact matches a registered member, the existing main-order rewards logic applies normally.

If the cashier rejects the Craft order, the Craft order is cancelled and reserved craft stock is restored.

The Craft Admin also has a manual transaction form:

- Craft Expense -> creates a normal main Expense with Craft Shop category.
- Craft Refund -> creates a normal main Expense with Craft Refund category.
- Craft Other Income -> creates a completed main `CRAFT/MISC` order.

All are also logged in the Craft transaction ledger for traceability.

## Craft Shop improvements

- Unified Admin authentication.
- Separate Craft Shop revenue visible in Master Admin.
- Recorded craft unit cost and gross-profit tracking.
- Main Cashier verification for online Craft orders.
- Cash and GCash payment choices.
- GCash reference capture.
- Stock reservation and cancellation restoration.
- In-stock and made-to-order/pre-order products.
- Active/archive, Featured, and Top Seller controls.
- Product likes, views, comments, and order counts.
- Customer customization/request notes.
- Persistent small image uploads stored as database data URLs, avoiding Render's ephemeral filesystem for new craft images.
- Uploaded legacy Craft Shop images are included under `static/craft/`.
- One Craft Admin page for inventory, orders, expenses, other income, refunds, and ledger review.

## Database

The integrated Craft Shop creates new tables in the same Food House database through `db.create_all()`:

- `craft_category`
- `craft_item`
- `craft_comment`
- `craft_order`
- `craft_ledger`

No existing Food House tables are deleted. Keep your existing production `DATABASE_URL` and database.

The uploaded standalone `Craft Shop.zip` contained an empty `instance/crafts.db`, so there were no local legacy rows to migrate from that file. The Craft Shop application features and image assets were merged into this build.

## Deployment

Replace the current Food House project files with this build, keep `.git`, `.env`, and your database credentials, then run:

```powershell
.\.venv\Scripts\python.exe scripts/predeploy_check.py
git status
git add .
git commit -m "Merge Craft Shop into main Macleens system"
git push origin main
```

After Render is Live, open `/admin/craft` while logged in as ADMIN.
