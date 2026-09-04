# Macleen’s Community — role security, tags, and rewards

Release: `2026.09.04-community-role-security-v2`

## What changed

- Student accounts receive only the Campus Hub dashboard. Resident accounts receive only Town Square. The opposite feed is filtered out by the server, not merely hidden with CSS.
- The Community now opens like a Facebook-style social page: the Wall is the only main view by default, while Alerts, Rewards, Gifts, People, Rankings, and Settings open as in-page tabs without reloading.
- Only the reserved `@uzu.macky` main-community-admin profile can switch between both feeds.
- New student applicants must upload one JPG, PNG, or WEBP student-ID image (maximum 3 MB) unless Admin already tagged their loyalty account as a known student.
- Student ID images are admin-only, are never returned by customer APIs or public templates, and are erased automatically when Admin approves or rejects the application.
- Admin can pre-approve a known student using the exact loyalty mobile number or card number. This is a private customer-account flag, not a public label.
- Existing residents may apply for Student access without losing Town Square during review. Approval changes the primary role to Student.
- Primary roles cannot be changed from normal profile settings or by modifying a browser request.
- Member wall posts are text-only, limited to 280 characters, and appear in strict newest-first order on their assigned community feed.
- Posts and comments support up to 10 valid `@handle` tags. Cross-feed tags are blocked except for the main admin; the tagged member receives an in-app notification.
- Members can follow/unfollow permitted handles without a page refresh. Following `@uzu.macky` for the first time earns `0.5` spendable loyalty points.
- Liking any `@uzu.macky` post for the first time earns `0.2` spendable loyalty points. Unliking/refollowing cannot earn the same reward again because each award has a unique database receipt.
- Likes, comments, reports, follows, connections, gifts, profile edits, student applications, notifications, polls, and vibe changes update in place without reloading the page.
- The previous Community features remain: first-post review, safety holds, report quarantine, streaks, Mystery Drops, aggregated group leaderboards, gifting, native ads, Flash Polls, Flash Perch alerts, optional Web Push, and Cashier redemption.

## First deployment setup

1. Deploy the full replacement package.
2. Open `/healthz` and confirm release `2026.09.04-community-role-security-v2`.
3. Open `/admin/community`.
4. If an existing profile already owns `@uzu.macky`, startup promotes it automatically. Otherwise, use **Assign reserved @uzu.macky main admin** and choose the owner’s existing community profile.
5. Use **Pre-approve known student** only after staff personally confirms the customer and records a valid reason under the store’s verification policy.

## Acceptance test

1. Register a Student test account. Confirm an ID image is required and the dashboard shows Campus Hub only.
2. Before approval, confirm posting, reactions, follows, connections, gifts, votes, and vibe changes are blocked.
3. In `/admin/community`, inspect the private ID, approve the student, and confirm the ID preview disappears immediately.
4. Confirm the approved Student still receives only Campus Hub. Create a Resident and confirm only Town Square is returned.
5. Sign in as `@uzu.macky`; confirm both feed buttons appear and work without a reload.
6. Post text containing another permitted `@handle`; confirm the post appears at the top and the tagged account receives a notification.
7. Follow `@uzu.macky`; confirm `+0.5` points once. Unfollow and refollow; confirm no second award.
8. Like an `@uzu.macky` post; confirm `+0.2` points once. Unlike and like again; confirm no second award.
9. Open every Facebook-style feature tab; confirm the Wall hides, the selected panel opens, and no browser reload occurs.
10. Test comment, connection, gift, poll, report, profile save, and notification actions; confirm the browser does not reload.

## Strong operational recommendations

1. Keep the Community invite-only for a 30-day pilot. A two-feed social network creates moderation and privacy work that can exceed its sales value.
2. Limit student-ID access to named administrators, publish a short retention notice, and review the process with a Philippine privacy professional before public launch.
3. Move private ID files to encrypted object storage with short automatic expiry if student volume grows. Database data URLs are acceptable for a small pilot, not ideal at scale.
4. Add CSRF protection and per-IP/device abuse monitoring before promoting rewards publicly.
5. Budget the `0.5` follow and `0.2` per-post-like rewards. Because every owner post is separately eligible, publish a monthly maximum in the rules or add an account-level monthly cap before a large launch.
6. Add a clear appeal and correction process for rejected student applications and removed posts.
7. Never use the keyword list to suppress respectful criticism or political viewpoints. Keep human review and written reasons.
8. Back up the production database before deployment and test a restore procedure.

## Data migration and rollback

The migration is additive. Existing products, customers, orders, points, cash flow, Crafts, Digital, Marketing, and investor data are preserved. A code rollback may leave the new Community tables and columns in place safely; do not delete production tables during rollback.
