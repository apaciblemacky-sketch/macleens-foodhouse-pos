# Hidden Treat v27 pending-only patch

Hidden Treat codes are now removed from the Cashier Counter Tray entirely.
They appear only in the **Pending Verification** section. Staff clicks
**Redeem free product** on the matching claim; the existing claim is marked
`REDEEMED`, the reserved stock is handed over to the customer, and the claim
disappears from Pending Verification on the next render. No POS order or
Counter Tray line is created.

The backend still keeps storefront voucher validation for customer checkout,
but the cashier sale screen no longer accepts or displays Hidden Treat codes.

## Files

- `app.py`
- `templates/cashier_pos.html`
- `scripts/hidden_treat_smoke_check.py`
- `scripts/predeploy_check.py`

Apply these files on top of the v26 patch, preserving the folder structure,
then restart/redeploy the service and hard-refresh the cashier page.
