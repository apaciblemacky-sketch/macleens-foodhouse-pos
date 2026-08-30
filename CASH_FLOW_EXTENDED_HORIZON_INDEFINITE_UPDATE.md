# Cash Flow Extended Horizon + Indefinite Recurrence Update

The Cash Flow Manager is no longer fixed to two years.

## Flexible planning horizon

- Start month remains selectable.
- Planning duration is selectable from **1 to 20 years**.
- The monthly summary expands automatically to the selected number of months.
- Daily drill-down remains available for every month inside the selected planning window.
- Actual sales always override projections.
- Blank sales days continue using the selected average/manual projection rules.
- COGS remains automatically calculated at **60% of sales**.

## Indefinite recurring income and expenses

Every Daily, Weekly, Bi-weekly, or Monthly cash-flow rule can now use **Indefinite / No End Date**.

An indefinite rule:

- begins on its selected start date;
- repeats according to its selected frequency;
- has no scheduled end date;
- continues affecting future cash-flow windows while the rule remains active;
- stops affecting forecasts only when paused, edited to a finite duration, or deleted.

Internally, `duration_count = 0` represents an indefinite schedule. Existing finite schedules remain unchanged.

The portal shows the number of occurrences and total amount contributed by an indefinite rule **within the currently selected planning window**, rather than pretending the lifetime total is finite.
