# Macleen's Investor Center Update

## What was added

- Public expansion page: `/investors`
- Private introduction form saved to the system
- Admin-only Investor Center: `/admin/investors`
- Funding goal and recorded-commitment settings (hidden publicly by default)
- Internal investor-readiness checklist
- Recorded performance, inventory, customer, and inquiry overview
- Investor Center button in Master Admin
- Expansion Vision button on the Food House storefront
- Private access-code page for proposed financing discussions
- Four selectable proposal packages with simple-interest calculations
- Counteroffer form routed to a Cashier Investor Proposals queue
- Cashier notes, status updates, reviewer name, and review timestamp

## Public story

The page now explains:

1. The customer promise: satisfaction, comfort, affordability, and convenience.
2. The long-term goal: become a leading community food house with a growing physical and online marketplace.
3. The three business areas:
   - Food House
   - Crafts and practical services
   - Future digital assets
4. Current challenges and the funded action for each:
   - Limited offerings → expand selected inventory and capacity
   - Limited seating → add tables, chairs, and practical space improvements
   - Low market presence → secure a domain and run measured Facebook visibility work
5. Funding priorities and a phased execution roadmap.

## Important investor-safety design

The public page does not publish returns, interest rates, or guaranteed outcomes. It does not accept money. It collects only a request for a private introduction.

Exact proposed terms are kept behind an Admin-set private access code. The private page clearly states that selections are non-binding discussion requests and that no money is accepted through the website.

## Private proposal options

All illustrations use straight-line simple interest with no compounding.

- ₱50,000 at 1.5% monthly for 24 months — lump sum at maturity. Total interest: ₱18,000; total maturity payment: ₱68,000.
- ₱100,000 at 1.5% monthly for 24 months — lump sum or monthly interest plus whole principal at maturity. Monthly interest: ₱1,500; total interest: ₱36,000; total across the term: ₱136,000.
- ₱250,000 at 2% monthly for 24 months — lump sum or monthly interest plus whole principal at maturity. Monthly interest: ₱5,000; total interest: ₱120,000; total across the term: ₱370,000.
- ₱500,000 at up to 2% monthly for 36 months — lump sum or monthly interest plus whole principal at maturity. At the displayed maximum: monthly interest ₱10,000; total interest ₱360,000; total across the term ₱860,000.

For monthly-interest choices, the final scheduled payment shown by the system includes the last month's interest plus the whole principal.

Before accepting funds, reconcile the system figures and prepare:

- a line-item use-of-funds budget backed by supplier quotations;
- verified sales, costs, expenses, inventory, bank, and GCash records;
- milestones, timing, responsibilities, and monthly reporting;
- a downside/risk plan; and
- a locally reviewed legal structure and written agreement.

## How to use it

1. Double-click `RUN_MACLEENS.bat`.
2. Log in as Admin.
3. Open **Investor Center**.
4. Edit the headline, summary, contact details, and funding figures.
5. Set a private proposal access code with at least 6 characters.
6. Leave **Show goal and recorded commitments** off until the amounts are verified.
7. Open the public page and share `/investors` only with appropriate contacts.
8. Give the private access code only to known prospects.
9. Cashier opens **Investor Proposals** from POS to review selections and counteroffers.
10. Admin completes due diligence and professional review before any money or agreement.

## Deployment

Double-clicking the run script starts the system locally. It does not deploy automatically. To put this update online, replace the existing project contents in the connected deployment repository, commit/push the changes, and redeploy on Render.

Keep `SECRET_KEY`, database credentials, and AI keys in Render Environment settings, not inside source files.
