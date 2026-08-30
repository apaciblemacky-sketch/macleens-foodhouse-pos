# Cash Flow Specific Sales Start Date Update

The 2-Year Cash Flow portal now lets Admin choose a starting date whenever **Use Specific Daily Sales Amount** is selected.

Behavior:
- Actual recorded sales always override projections.
- On blank days **before** the chosen manual start date, the selected 3/7/15/30/Lifetime actual-sales average is used.
- On blank days **on or after** the chosen manual start date, the configured specific daily sales amount is used.
- COGS remains automatic at 60% of the sales amount used for that day.
- Switching back to Average mode preserves the last specific amount and start date so they are ready if Manual mode is selected again.
