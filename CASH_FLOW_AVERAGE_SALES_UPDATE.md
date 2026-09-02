# Cash Flow Lifetime Actual-Sales Basis

The Cash Flow Manager now automatically fills every blank sales day with an average daily sales projection.

## Average basis
- The average uses every recorded day with positive actual sales up to the current Philippine date.
- Actual sales follow the existing Macleen's project policy: completed POS sales plus Vault Drops.
- Blank days are excluded from the average itself because they are the days being projected.
- “Sample work” income is excluded from this history without deleting its source record.
- If no included actual sales days exist yet, the actual-sales average remains ₱0.00 and the filtered break-even requirement is used.

## Forecast behavior
- A day with actual sales keeps its real sales amount.
- A day without actual sales uses the higher of the lifetime actual-sales average or that month's filtered break-even requirement.
- COGS is automatically calculated as 60% of whichever sales value is used for that day.
- The 24-month summary therefore combines actual sales and projected average sales.
- Daily rows visibly identify ACTUAL versus BREAK-EVEN + ACTUALS so projections are not mistaken for recorded transactions.

Bi-weekly recurring income/expense schedules remain available and unchanged.
