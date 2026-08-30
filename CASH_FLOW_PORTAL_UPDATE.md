# Macleen's Food House — 2-Year Cash Flow Portal

## New portal
Admin can open **2-Year Cash Flow** from the Admin header or visit:

`/admin/cash-flow`

The portal always displays a 24-calendar-month window. The start month can be changed at any time.

## Cash-flow calculation
For this portal only:

- **Sales** = completed daily order sales + Vault Drops, preserving the current Macleen's accounting policy.
- **COGS** = exactly **60% of Sales**.
- **Gross Profit** = Sales - COGS.
- **Additional Income** = active recurring income rules that fall on the day/month.
- **Expenses** = active recurring expense rules that fall on the day/month.
- **Net Cash Flow** = Sales + Additional Income - COGS - Expenses.

Future sales are not guessed or forecast. A future date remains at zero sales until actual completed sales are recorded.

## Recurring expenses and additional income
Each cash-flow rule has:

- Type: Expense or Additional Income
- Title / description
- Amount per occurrence
- Frequency: Daily, Weekly, or Monthly
- Start date
- Duration / number of occurrences
- Optional category
- Optional notes

Maximum duration is intentionally bounded to the two-year planning use case:

- Daily: up to 730 occurrences
- Weekly: up to 104 occurrences
- Monthly: up to 24 occurrences

Rules can be edited, paused/resumed, or deleted. Paused rules stay saved but stop affecting cash-flow totals.

## Views
The portal includes:

- 24-month summary table
- running net cash flow
- daily detail for any month in the selected two-year period
- separate daily POS sales and Vault Sales columns
- total sales, 60% COGS, additional income, expenses, and daily net cash flow

## Database
A new `cash_flow_plan` table is created automatically by `db.create_all()` during application startup. No destructive database migration is required.

The update ZIP intentionally does not include `instance/foodhouse_pos.db`, so replacing project files will not overwrite an existing local database.
