# Macleen’s Community — public-beta configuration

Release: `2026.09.04-community-project-cover-v7`

The complete specification, reasons, limits, emergency switches, database
recommendation, and test checklist are in `COMMUNITY_LITE_SCALE_UPDATE.md`.

## Customer experience

- The Wall remains the main Facebook-style view.
- Student accounts receive Campus Hub only; Resident accounts receive Town
  Square only. `@uzu.macky` is the sole profile that can administer both.
- Member profiles are viewable within the authorized role community and may be
  locked to the owner, accepted connections, and Community Admin.
- People provides role-safe suggestions, follows, and connections.
- Word-only posts, mentions, likes, and comments update without page refreshes.
- The first three approved posts establish trust; later safe posts publish
  immediately. Keyword hits and three-report quarantines still require review.
- Role-locked project workspaces provide progress tracking, assigned tasks,
  shared notes, polls, members, and an optional Facebook Messenger link.
  Internal chat is not part of the Community.
- Campus categories include Study & Collab, Campus Board, Buy & Sell,
  Discussions, and Lost & Found.
- Any member can upload a compressed profile cover photo. A post can tag up to
  25 eligible people. The Main Admin profile has no student/resident metadata.
- Digital Business, purchase-based loyalty, Flash Perch alerts, and useful
  role-targeted promotions remain available.

## Privacy and rewards

Student applicants show a current ID privately to staff; the system does not
accept or retain the ID image. Staff may pre-approve a known loyalty customer.
Mobile numbers, PINs, addresses, balances, and purchase histories remain private.

Likes and follows do not award spendable points. New peer gifts, public reshares,
streak prizes, Mystery Drops, and leaderboards are paused during the beta.
Existing issued vouchers remain redeemable.

## Deployment check

1. Deploy the complete flat replacement package.
2. Open `/healthz` and confirm
   `2026.09.04-community-project-cover-v7`.
3. Open `/admin/community` and review the safety-control status.
4. Before a large launch, configure managed PostgreSQL as `DATABASE_URL` and
   confirm `/healthz` reports `postgresql`.
5. Run the acceptance checklist in `COMMUNITY_LITE_SCALE_UPDATE.md`.
