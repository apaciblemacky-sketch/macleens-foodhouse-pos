# Pending Order Adjustment Update

This release builds on the Product Sub-options Update.

## New Cashier capability

For any order still in **VERIFICATION**, the Cashier queue now includes a **＋₱ ADJUST** button.
Use it when a customer's note requests an extra item or service that was not included in the original checkout total.

Examples:
- Extra rice
- Additional sauce or packaging
- Rush/custom service fee
- Other manually confirmed add-on requested in the customer's note

The Cashier enters:
- description of the extra item/service
- quantity
- fee per unit
- optional updated cash received/change-for amount for CASH orders

The system adds the charge as a separate `[Cashier Add-on]` order item and updates the pending order subtotal/total before the order is accepted.

## Safety rules

- Only orders with status `VERIFICATION` can be adjusted.
- Extra fees must be positive and quantities must be 1–99.
- Original customer product lines cannot be removed through this tool.
- Only lines created by the Cashier adjustment feature can be removed.
- Removing an added charge reverses only that charge from the total.
- CASH orders cannot be accepted when the recorded cash received/change-for amount is below the adjusted total.
- GCASH adjustments warn the Cashier to collect/confirm the additional amount before accepting.
- Customer notes remain visible in the adjustment modal.
- Adjustment activity is recorded in the order's internal collection/audit notes.
- Existing product stock is not changed for manual service/additional-fee lines.

## Unchanged

- Product sauce/flavor sub-options remain active.
- Product-specific cashier amounts and minimum amounts remain active.
- Customer portal simplification remains active.
- Vault Drop remains part of gross sales per project policy.
