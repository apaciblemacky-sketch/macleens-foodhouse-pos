# Macleen’s Community — profiles, social wall, and group collaboration

Release: `2026.09.04-community-group-collaboration-v5`

## What changed

- Student accounts receive only the Campus Hub dashboard. Resident accounts receive only Town Square. The opposite feed is filtered out by the server, not merely hidden with CSS.
- The Community now opens like a Facebook-style social page: the Wall is the only main view by default, while Alerts, Rewards, Gifts, People, Chats, Rankings, and Settings open as in-page tabs without reloading.
- Every allowed member handle opens a dedicated community profile. Same-role public profiles show public bio, role metadata, community score, follower counts, and that member’s word-post wall; private loyalty data never appears.
- People now shows role-safe suggested accounts, current follows, and accepted/pending connections. Follow and connection actions update without a page refresh.
- A member can lock their profile. Locked profiles show only a minimal identity card until the viewer is the owner, an accepted connection, or Community Admin.
- Verified members can like, comment, and reshare posts without a page refresh. A reshare becomes a word-only wall post and references the original post.
- Community Admin now has a private unread inbox for every new member join, student-access application, and replacement student-ID submission. The `@uzu.macky` in-app Alerts tab receives the same admin-safe event.
- Verified members can create invite-only group chats for up to 25 members. Every group is permanently bound to Campus Hub or Town Square, and invitees must accept before they can read it.
- Each private group includes Messenger-style chat, assignable tasks with due dates and statuses, collaborative notes with pin/archive controls, and live single-choice polls.
- Messages poll every five seconds and chat, task, note, poll, invitation, removal, and leave actions update without a full-page refresh. Opening a newly created group or returning after leaving intentionally navigates to another page.
- Ordinary private group messages do not appear in Admin. Only messages held by a safety phrase or reported by a group member enter the private safety queue. Group chats are not end-to-end encrypted.
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
2. Open `/healthz` and confirm release `2026.09.04-community-group-collaboration-v5`.
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
10. In Chats, create a same-role group, accept an invitation from a second account, exchange messages, assign and complete a task, edit/pin a note, and vote in a poll. Confirm these interactions do not reload the browser.
11. Try opening that group as an opposite-role member and before accepting an invitation; confirm access is denied.
12. Report a test group message. Confirm only the reported message appears in Admin’s private group-message queue, then allow or remove it.
13. Test comment, connection, gift, report, profile save, and notification actions; confirm the browser does not reload.

## Strong operational recommendations

1. Keep the Community invite-only for a 30-day pilot. A two-feed social network creates moderation and privacy work that can exceed its sales value.
2. Limit student-ID access to named administrators, publish a short retention notice, and review the process with a Philippine privacy professional before public launch.
3. Move private ID files to encrypted object storage with short automatic expiry if student volume grows. Database data URLs are acceptable for a small pilot, not ideal at scale.
4. Treat group chat as pilot collaboration—not a replacement for Messenger yet. Five-second polling is practical for a small launch, but move to WebSockets or server-sent events before high chat volume.
5. Publish a group-chat retention and deletion policy. The current safety model is invite-only but not end-to-end encrypted, so users must not treat it as a confidential records channel.
6. Add CSRF protection and per-IP/device abuse monitoring before promoting rewards publicly.
7. Budget the `0.5` follow and `0.2` per-post-like rewards. Because every owner post is separately eligible, publish a monthly maximum in the rules or add an account-level monthly cap before a large launch.
8. Add a clear appeal and correction process for rejected student applications and removed posts.
9. Never use the keyword list to suppress respectful criticism or political viewpoints. Keep human review and written reasons.
10. Back up the production database before deployment and test a restore procedure.

## Data migration and rollback

The migration is additive. Existing products, customers, orders, points, cash flow, Crafts, Digital, Marketing, and investor data are preserved. A code rollback may leave the new Community tables and columns in place safely; do not delete production tables during rollback.
