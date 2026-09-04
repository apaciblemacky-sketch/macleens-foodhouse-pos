# Macleen’s Community Lite v6

Release: `2026.09.04-community-lite-scale-safety-v6`

This is the recommended public-beta shape of the Community. It keeps the parts
that directly support loyalty, repeat visits, useful local information, and
Macleen’s digital products while pausing features that create disproportionate
database load, fraud, privacy exposure, or moderation work.

## What remains available

- role-separated Campus Hub and Town Square feeds
- `@handle` profiles, optional profile lock, follows, likes, comments, mentions,
  notifications, reports, and blocks/connections
- Town Square classifieds and Campus study/collaboration categories
- word-only posts, newest first, with a 25-post page window
- first three posts reviewed by staff; safe trusted posts publish immediately
- keyword safety holds and three-report quarantine pending human review
- Admin summaries for new members and pending student checks
- small invite-only group workspaces with tasks, shared notes, and polls
- optional external Messenger group link set by the workspace owner
- loyalty balance, purchase-based punch card, Flash Perch alerts, relevant store
  promotions, and the Digital Business link
- AJAX interactions so ordinary Community actions do not refresh the page

## What is paused and why

- Social points for following or liking: prevents easy loyalty-point farming.
- Peer point/product gifting: protects balances and inventory while the beta is
  small and processes are still being proven.
- Public reshares: avoids duplicate feed content and reduces moderation volume.
- Community streaks, Mystery Drops, and leaderboards: removes daily write load,
  reward liability, and incentives for low-quality activity.
- Internal Messenger-style chat and five-second polling: removes continuous
  requests and sensitive-message storage. Workspaces retain tasks, notes, polls,
  and may link to Messenger externally.
- Student-ID image uploads: no new ID image is accepted. Existing stored ID blobs
  are erased by the migration. Staff can pre-approve a known loyalty customer or
  visually check a current ID in person without keeping a copy.
- Per-view ad counters: only deliberate ad clicks are recorded. This avoids a
  database update every time an ad enters a screen.
- One notification per new member: Admin now sees daily join and pending-student
  counts. Verification and safety events remain individual alerts.

Historical records and database tables are not destructively removed. Existing
issued vouchers stay redeemable at Cashier, but customers cannot create new ones.

## Safety limits

- first 3 posts require approval (`COMMUNITY_TRUSTED_POST_THRESHOLD`)
- maximum 2 active workspaces owned by a member (`COMMUNITY_MAX_OWNED_GROUPS`)
- maximum 25 members in a workspace
- maximum 5 posts per hour and 20 comments per hour per profile
- maximum 10 reports per day per customer
- up to 25 recent posts are loaded per visible role feed
- non-admin members receive only their server-authorized role channel

## Emergency controls on Render

Set an environment variable to `false`, then redeploy:

- `COMMUNITY_REGISTRATION_OPEN` — pauses new Community profiles
- `COMMUNITY_POSTING_OPEN` — pauses new posts and comments
- `COMMUNITY_GROUP_WORKSPACES_OPEN` — pauses new workspaces

Keep these disabled in the beta unless you deliberately reverse the decision:

- `COMMUNITY_INTERNAL_CHAT_OPEN=false`
- `COMMUNITY_SOCIAL_REWARDS_OPEN=false`
- `COMMUNITY_GIFTING_OPEN=false`
- `COMMUNITY_RESHARING_OPEN=false`

The current state of every control is shown at `/admin/community`.

## Strong production recommendation

Do not invite thousands of members while production uses the bundled SQLite
database. Create a managed PostgreSQL database, back up and migrate the existing
production data, and set its internal connection URL as `DATABASE_URL` in the
Render web service. The `/healthz` response and Community Admin page warn when a
production instance is still on SQLite.

The Render start command intentionally uses one Gunicorn worker and four threads.
This is safer for the bundled SQLite fallback. After PostgreSQL, object storage,
backups, monitoring, and load testing are confirmed, worker/instance scaling can
be increased deliberately.

Do not keep customer uploads or a live production database only on an ephemeral
web-service disk. Use managed storage, daily backups, rate-limit monitoring, and
a tested restore procedure before a large public announcement.

## Verification after deployment

1. Open `/healthz` and confirm the release and database type.
2. Open `/admin/community` and review the Community Lite controls and warnings.
3. Test one Student and one Resident account; neither may see the other feed.
4. Confirm the first three posts enter Admin review and the fourth safe post is
   immediate after the earlier three are approved.
5. Confirm likes, follows, comments, tasks, notes, and polls do not refresh pages.
6. Confirm reshare, gifting, and group-message APIs report that they are paused.
7. Confirm student signup requests an in-person visual check and stores no image.
8. Test the three emergency switches during a planned maintenance window.

Local checks:

```text
python scripts/predeploy_check.py
python scripts/community_smoke_check.py
```
