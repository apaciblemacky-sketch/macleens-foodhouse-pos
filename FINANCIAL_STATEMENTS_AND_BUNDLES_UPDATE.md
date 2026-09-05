# Financial Statements & Bundle Deals — v9

## New Admin Portal

Open **Admin Control → Financial Statements**, or visit:

`/admin/financial-statements`

The portal contains five tabs:

1. **Income Statement** — revenue, cost of goods sold, operating expenses, gross profit, and net income for the selected period.
2. **Balance Sheet** — assets, liabilities, and equity as of the selected end date.
3. **Statement of Cash Flows** — operating and financing cash movements, plus any manual cash adjustments. The separate Investing Activities section has been removed.
4. **Journal & Adjustments** — compressed and expanded debit/credit entries plus manual adjusting entries.
5. **Cash Flow Manager Recurring Plans** — a single report-only control for each recurring Cash Flow Manager plan.

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

Personal withdrawals should normally be recorded as **Owner Drawings**, not operating expenses. The portal includes completed cashier/POS sales, vault drops, and direct expenses at all times. If a recurring personal or non-business item was set up in **Cash Flow Manager**, use the recurring-plan control to remove the whole series from a business-only view without losing the operational audit record.

## Cash Flow Manager Exclusions

The report never offers an exclusion button for an individual cashier/POS sale, vault drop, direct expense, or single paid bill. Those sources are always included.

For a Cash Flow Manager recurring plan, choose **Exclude full series** once. It removes every paid, unpaid, and scheduled occurrence of that plan from the Financial Statements. Choose **Include full series** to restore all occurrences. The original Cash Flow Manager plan and payment history are never deleted or edited.

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
