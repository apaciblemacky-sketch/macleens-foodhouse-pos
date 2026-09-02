# Macleen's Investor Center Update

## Private-only investor workflow

- No investor or expansion link is shown on the Food House storefront.
- Legacy investor URLs redirect to the access-code invitation page.
- Admin-only Investor Center: `/admin/investors`
- Private access-code invitation page: `/investors/private-offer`
- Funding goal and recorded-commitment settings for private materials
- Internal investor-readiness checklist
- Recorded performance, inventory, customer, and inquiry overview
- Investor Center button in Master Admin
- Four selectable proposal packages with simple-interest calculations
- Counteroffer form routed to a Cashier Investor Proposals queue
- Cashier notes, status updates, reviewer name, and review timestamp

## Private business story

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

The storefront does not advertise investor access. Exact proposed terms are kept behind an Admin-set private access code and shared only with selected contacts. The private page states that selections are non-binding discussion requests, no money is accepted through the website, and final arrangements require due diligence, professional review, and a separate signed agreement.

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
6. Leave funding figures hidden until the amounts are verified.
7. Share `/investors/private-offer` only with selected contacts.
8. Give the private access code only through a direct private conversation.
9. Cashier opens **Investor Proposals** from POS to review selections and counteroffers.
10. Admin completes due diligence and professional review before any money or agreement.

## Deployment

Double-clicking `RUN_MACLEENS.bat` starts the system locally. It does not deploy automatically.

To deploy through the existing VS Code → GitHub → Render workflow:

1. Put the replacement contents inside the GitHub-connected project folder.
2. Double-click `DEPLOY_TO_RENDER.bat`.
3. Review the displayed repository and changed files.
4. Type `DEPLOY` when asked.
5. Enter a commit message or press Enter for the default.
6. Sign in to GitHub if requested.
7. Watch the Render Events page until the new deployment is Live.

The deployment script stops if it is not inside a Git repository, is not on `main`, has no `origin`, or fails the safety check. It never force-pushes and does not contain a Render deploy hook or secret.

Keep `SECRET_KEY`, database credentials, and AI keys in Render Environment settings, not inside source files.
