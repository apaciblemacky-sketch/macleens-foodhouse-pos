# Hidden Treat v25 patch

This patch adds the requested account-wide rule: a customer can successfully
win only one Hidden Treat every three days. The API rejects early claims and
customer-facing placement helpers hide other active treats while the cooldown
is running. The existing one-claim-per-hunt rule remains in place.

It also changes cashier redemption of a free-product Hidden Treat into a direct
claim handoff. The reserved unit is released to the customer and an audit event
is recorded, but no zero-value `Order` or `OrderItem` is created, so the prize
does not appear in the Counter Tray, sales totals, or BIR sales records.

## Files in this patch

- `app.py`
- `templates/admin.html`
- `scripts/hidden_treat_smoke_check.py`
- `scripts/predeploy_check.py`

Apply these files on top of the previously delivered v24 auto-link patch,
then restart/redeploy the service. Run the two included checks (and the full
regression set if available) before going live.
