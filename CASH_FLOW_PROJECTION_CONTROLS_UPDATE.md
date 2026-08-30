# Cash Flow Projection Controls Update

Added persistent Admin controls to the 2-Year Cash Flow portal.

- Blank sales days can use either a calculated actual-sales average or a specific daily sales amount.
- Average ranges: most recent 3, 7, 15, or 30 actual positive-sales days, or Lifetime.
- Blank/no-sale days are excluded from the averaging sample.
- Actual recorded sales always override the projection.
- A one-click **Use Average Again** action switches a manual projection back to the selected average range.
- COGS remains automatically calculated at 60% of actual or projected sales.
- Macleen's existing project rule that Vault Drops are included in sales is unchanged.
- Projection preferences are stored in `StoreSetting`; no destructive database migration is required.
