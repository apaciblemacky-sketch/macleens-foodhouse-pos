# Macleen's Business / Finance / Analytics / Social Update v39

This package is an **incremental replacement update for release v38** (`2026.09.12-security-auto-host-mobile-share-v38`).
Extract it into the existing Macleen's project root and choose **Replace files in destination**.

**No database reset is required.** New tables/columns are additive and are created/migrated at startup.

## What changed

### Digital product sharing
- Digital product links now have Storefront-style Facebook/Open Graph/Twitter thumbnails.
- Each Digital product gets a 1200x630 social preview image and a Share Product action.

### Internal Daily Sales Record
- System sales are shown as **one consolidated row per Philippine calendar day**, not one row per transaction.
- A separate **Blank / Manual Daily Sales Record** lets Admin enter a date, receipt/reference number, specific sales amount, notes, and whether to include that figure in Financial Statements.
- Manual figures are kept separate from system-computed daily totals to reduce accidental double counting.

### Financial Statements
- Added/checkable expense accounts: Payroll & Labor, Rent, Electricity, Water, Internet & Communications, Taxes & Permits, Payment & Bank Fees, Insurance, Marketing, Supplies & Ingredients, Transport, Repairs & Maintenance, General & Miscellaneous, Depreciation, and legacy Rent & Utilities.
- Added **Products & Cost** tab for Food, Crafts, and Digital products.
- Product rows show Selling Price, Cost, units sold, period sales, Sales %, Cost %, and gross-margin %.
- Admin can edit Selling Price and Cost from the Financial Statements page.
- Added independent **Vault Drop Sales %** and **Vault Drop Cost %** settings.

### Cashier POS
- Removed the Burger/Nachos promotion shortcut buttons from the top of Cashier POS.
- Existing historical promo records/routes are retained for compatibility.

### Portal About / Announcements
- Food/Storefront, Crafts, and Digital each have their own separately editable **About** section.
- Existing separate announcement boards remain available per portal.
- Crafts public heading now says pickup **and delivery** are available instead of pickup-only wording.
- Public Crafts visitor/unique-view counters are removed.

### Website analytics
- Storefront, Crafts, and Digital now record daily Visits + privacy-conscious Unique Visitors.
- Interactive Admin graph supports 7 / 30 / 90 / 365 days, Visits vs Unique Visitors, portal toggles, and hover/tap details.
- **AI Suggestion** analyzes aggregate traffic only. If a configured AI provider is unavailable, the system returns a local rule-based suggestion instead.
- Unique-visitor history begins after this upgrade; old anonymous unique-visitor history cannot be reconstructed safely.

### Facebook automation preparation
Page posting and Group posting are deliberately separate:

**Facebook Page**
- `META_PAGE_ID`
- `META_PAGE_ACCESS_TOKEN`
- optional `META_GRAPH_VERSION`

**Facebook Group automation bridge**
- `FB_GROUP_POSTING_WEBHOOK_URL`
- optional `FB_GROUP_POSTING_WEBHOOK_TOKEN`

This keeps the Page account/token separate from the Group automation account/provider. See `FB_AUTOMATION_SETUP.md`.

### Support page
- Keeps QR PH support payments.
- Adds PayPal support payments.
- Adds **Invest** action linking to the existing Investor area.

### Project maintenance / Claude findings
- Added shared `static/macleens-shared.css` and connected it to high-traffic pages as the first stage of reducing inline-style duplication.
- Added `.gitignore` protection for SQLite DBs, DB sidecars, backups, ZIPs, `.env`, virtual environments, and Python cache files.
- Added `scripts/backup_database.py` which puts local SQLite backups **outside the Git project** and verifies SQLite integrity.
- Added `PROJECT_MAINTENANCE_GUIDE.md` with a safe gradual plan for splitting the very large `app.py` later. This release does **not** attempt a risky full refactor.
- Updated `scripts/predeploy_check.py` for the current QR PH/PayPal/chat/hosted-app schema.
- Added `scripts/v39_business_upgrade_smoke_check.py`.
- Updated `DEPLOY_TO_RENDER.bat` to back up the DB, run checks, require a descriptive commit message, then push to GitHub/Render.

## Recommended deployment

1. Back up your current project folder.
2. Extract this ZIP into the existing project root.
3. Choose **Replace files in destination**.
4. Do not delete `.env`, production environment variables, uploaded assets, or your database.
5. Preferred: run `DEPLOY_TO_RENDER.bat` from the project root.

The deployment script will:
1. back up the local SQLite database outside the repository;
2. run pre-deploy checks and smoke tests;
3. show changed Git files;
4. ask you to type `DEPLOY`;
5. ask for a descriptive commit message;
6. push `main` to GitHub so Render can deploy.

Suggested commit message:

`Improve daily sales, financials, analytics, portals, and social automation`

Manual Git alternative:

```bash
git status
python scripts/predeploy_check.py
python scripts/v39_business_upgrade_smoke_check.py
git add .
git commit -m "Improve daily sales, financials, analytics, portals, and social automation"
git push origin main
```

## Post-deploy checks

- Open `/healthz` and confirm release: `2026.09.12-daily-sales-finance-analytics-social-v39`.
- Share one Food product and one Digital product link to verify thumbnails.
- Open **Daily Sales Record** and add one test manual daily row (delete it after testing if needed).
- Open Financial Statements → **Products & Cost** and verify product prices/costs.
- Test Vault Drop Sales % / Cost % settings.
- Check Food, Crafts, and Digital About + Announcement sections.
- Open analytics and try 7/30/90-day views plus AI Suggestion.
- Confirm Crafts no longer shows public visitor counters or pickup-only wording.
- Verify Cashier POS no longer has top Burger/Nachos promo buttons.
- Verify Facebook Page and Group automation settings remain separate.

## Verification completed while packaging

- `app.py` and `marketing_agent.py` Python compilation: PASS
- `scripts/predeploy_check.py`: PASS
- `scripts/v39_business_upgrade_smoke_check.py`: PASS
- SQLite backup utility + integrity check: PASS

The container used to build this package does not have Flask/Werkzeug installed, so the older runtime smoke scripts that import the live Flask app could not be executed here. `DEPLOY_TO_RENDER.bat` runs those scripts in your normal project Python environment before it pushes.
