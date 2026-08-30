# Cash Flow Portal Redeploy Fix

This package adds two valid URLs for the portal:

- `/admin/cash-flow`
- `/admin/cashflow`

The Admin header links with Flask `url_for('cash_flow_portal')` instead of a hard-coded URL.

Before committing on Windows PowerShell, run:

```powershell
.\scripts\verify_cashflow_portal.ps1
python scripts/predeploy_check.py
```

If both pass, commit and push the same project folder that Render is connected to.
