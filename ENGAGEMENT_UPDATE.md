# Macleen's Food House — In-Store Engagement & Marketing Update

This update builds on the Stability Upgrade and keeps the existing project policy that Vault Drops are included in gross sales.

## Customer portal changes

The customer portal is now a walk-in benefits hub first and an online ordering tool second. The dashboard opens with four primary actions:

- My Rewards
- Free Wi-Fi
- Vote & Earn
- Today's Member Deals

Walk-in purchases continue to earn normal rewards when the cashier selects the registered member before recording the paid sale.

### Rewards progress

The dashboard shows the member's current points, progress toward the 20-point milestone, recent reward activity, and explains that walk-in purchases count.

### Vote & Earn + Wishlist

Members can vote for active menu products and save products to a wishlist. Products are grouped by menu category. The first Vote or Wishlist action in each ISO week earns +2 points; additional votes/wishlist actions in the same week remain available but do not award extra engagement points.

### Free Wi-Fi

New members receive 10 minutes on registration. That welcome allocation counts as that Philippine day's free Wi-Fi claim. On later Philippine calendar days, a member can claim +10 minutes once per day from the portal. Existing cashier Wi-Fi top-ups remain available.

### Referrals

New referrals are now validated by a real paid purchase. A referred member registers with the referrer's card/link, then after the referred member's first completed paid purchase:

- referrer receives +2 points
- referred member receives +2 points

Legacy signup referral bonuses are detected so an older referrer is not paid twice.

### Member promotions and timed bonus campaigns

Admin can create:

- 3-day member deals, including portal-only deals hidden from the public storefront
- fixed bonus-point campaigns
- double-points or other points-multiplier campaigns
- minimum-spend campaigns
- campaigns restricted by date, day of week, and time window (useful for slow hours)

Campaign awards are recorded per order to prevent the same campaign from awarding twice to one transaction.

## In-store QR system

A dynamic QR system generates the correct live hostname automatically, so the same code works on Render or another domain.

Admin QR Kit: `/admin/marketing/qr-kit`

QR entry points:

- `/portal/start/counter` — registration / member benefits at cashier
- `/portal/start/table` — Vote & Earn while waiting
- `/portal/start/receipt` — rewards check after purchase
- `/portal/start/facebook` — social / printed promotions
- `/portal/start/wifi` — daily Wi-Fi claim

The cashier includes a New Member QR button, and printed cashier order slips include the receipt rewards QR.

## Marketing measurement

Admin now shows:

- QR scans in the last 7 days
- portal logins in the last 7 days
- new registrations in the last 7 days
- counter-sourced registrations in the last 7 days
- Wi-Fi claims in the last 7 days
- weekly votes
- total wishlist saves
- rewarded referrals
- categorized weekly vote results

## Database additions

New tables are created automatically by `db.create_all()`:

- `customer_wishlist`
- `menu_vote`
- `engagement_claim`
- `bonus_campaign`
- `bonus_campaign_claim`
- `referral_reward`
- `portal_event`

`promotion_tracker` receives two additive columns:

- `description`
- `portal_only`

The bundled local SQLite database has also been updated to match.

## New dependency

`qrcode>=7.4.2` is included in `requirements.txt` for dynamic SVG QR generation.

## Deployment

After replacing the project folder contents, run:

```bash
git status
git add app.py templates static scripts requirements.txt .gitignore STABILITY_UPGRADE.md ENGAGEMENT_UPDATE.md
git commit -m "Add in-store rewards and marketing engagement system"
git push origin main
```

Then watch the Render deployment log. The application will add the new PostgreSQL tables/columns automatically on startup.

## Validation

Run locally from the project root when Python is available:

```bash
python scripts/predeploy_check.py
```

The check verifies source compilation, template targets, bundled SQLite schema, the Vault Drop accounting policy, and the new engagement-system markers.
