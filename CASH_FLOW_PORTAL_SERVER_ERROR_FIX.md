# Cash Flow Portal Server Error Fix

This hotfix corrects the cash-flow daily-detail template after the average-sales projection update.

## Root cause
The daily table accidentally referenced monthly summary fields (`actual_sales`, `actual_days`, `projected_sales`, `projected_days`) that do not exist on daily rows. Jinja formatting of those undefined values caused the `/admin/cash-flow` request to return a server error.

## Fix
- Removed the invalid monthly-only cell from the daily table.
- Restored the 9-column daily layout: Date, Source, POS Sales, Vault Sales, Total Sales, COGS 60%, Additional Income, Expenses, Net Flow.
- Added a pre-deploy safeguard that fails if monthly-only fields are ever copied into the daily table again.
- Preserved average daily sales projections, 60% COGS, bi-weekly schedules, and all previous cash-flow behavior.
