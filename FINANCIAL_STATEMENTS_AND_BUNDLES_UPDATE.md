# Financial Statements & Bundle Deals — v8

## New Admin Portal

Open **Admin Control → Financial Statements**, or visit:

`/admin/financial-statements`

The portal contains five tabs:

1. **Income Statement** — revenue, cost of goods sold, operating expenses, gross profit, and net income for the selected period.
2. **Balance Sheet** — assets, liabilities, and equity as of the selected end date.
3. **Statement of Cash Flows** — operating, investing, and financing cash movements.
4. **Journal & Adjustments** — compressed and expanded debit/credit entries plus manual adjusting entries.
5. **Included Sources** — visible controls to include or exclude a reporting source without editing/deleting the original POS or cash-flow record.

## How Automatic Entries Work

The system creates report-only double-entry lines whenever the portal is opened:

- Completed cash/GCash orders: Cash & Digital Collections → Sales.
- Completed credit orders: Accounts Receivable → Sales.
- Completed orders with a recorded item cost: Cost of Goods Sold → Inventory.
- Vault drops: Cash & Digital Collections → Food & Beverage Sales; COGS uses the fallback Cost % because vault drops have no item-level cost record.
- Direct system expenses: Expense account → Cash & Digital Collections.
- Paid cash-flow plan expenses: Expense account → Cash & Digital Collections.
- Optional unpaid cash-flow plan expenses: Expense account → Accounts Payable.
- Optional scheduled income plans: Accounts Receivable → Other Income.

Automatic entries are generated from their source records and are not stored as duplicates. Their accounting assumptions are shown in the portal.

## Important Accuracy Notes

This is a management-reporting tool. It can make the existing system much clearer, but it cannot reconstruct opening cash, bank/GCash balances, loans, prior inventory purchases, or owner capital that were never entered. The Balance Sheet therefore shows an **Unreconciled opening balance / capital** line when needed to balance old history.

Before using this as an official statement:

1. Count cash on hand and reconcile GCash/bank balances.
2. Confirm customer receivables and unpaid bills.
3. Check physical inventory and item costs.
4. Record opening cash, capital, loans, equipment, or corrections using a balanced manual adjustment.
5. Have a qualified Philippine accountant review reports needed for tax, BIR, lending, or investor decisions.

Personal withdrawals should normally be recorded as **Owner Drawings**, not operating expenses. The portal includes every original source by default because the owner requested full visibility; use Included Sources to remove personal items from a business-only view without losing the audit record.

## Profit Margin % and Cost %

- **Target Profit Margin %** is a planning target shown beside the report. It does not change actual historical revenue or expenses.
- **Fallback Cost %** estimates COGS only when a completed sale has no recorded product cost. It is also used for direct vault drops. The source row is marked as estimated in the expanded journal.

Always enter product costs in the catalog whenever possible. Recorded costs are more reliable than a percentage estimate.

## Manual Adjusting Entries

Use Journal & Adjustments for an entry such as:

- Debit: Cash & Digital Collections
- Credit: Owner Capital
- Amount: opening cash amount

Every manual entry creates exactly one debit and one credit line for the same amount. You can remove a mistaken manual entry; automatic source records remain untouched.

## Bundle Deals

Open **Admin Control → Product Bundle Deals & Discounts**.

1. Enter a bundle name and optional customer-facing description.
2. Choose **Percent** or **Fixed peso** discount.
3. Add the active products and quantities.
4. Create the deal.

The storefront displays the regular total, savings, and final bundle price. Customers add the bundle as one basket item. At checkout the server expands it into the included product lines, recalculates the discount, copies each product cost, and deducts stock from each product.

For safety, fixed bundles only accept products without required sub-options or priced sizes. This avoids choosing a flavor, sauce, or size on behalf of a customer. Products with choices can still be sold normally.

## Checks Included

`scripts/financial_bundle_smoke_check.py` verifies bundle pricing/stock expansion, balanced automatic journal entries, report calculations, manual adjustments, and both new pages. `DEPLOY_TO_RENDER.bat` runs it before a push.
