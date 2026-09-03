# Macleen’s Community Hub — release and operating guide

Release: `2026.09.03-community-v1`

## What is implemented

- Optional public handles layered over private loyalty accounts. The feed never displays mobile numbers, PINs, addresses, loyalty balances, or purchase history.
- Students can write in Campus Hub and read Town Square. Residents have the inverse permission.
- Student fields: campus, department, graduating year, vibe. Resident fields: official Binalbagan barangay and resident-since year.
- Mutual handle-based connections protect student Vibe status; it appears only to accepted connections, not every feed reader.
- Text posts (280 characters), one compressed image, optional safe public link, and 2–4 choice polls.
- First post approval. Later safe posts publish immediately; configured phrase matches wait for human review.
- Three unique open reports temporarily quarantine a post. A person must publish, hide, or remove it; there is no automatic permanent shadowban.
- Daily check-in streak, 7-day one-use 1.5× points bonus, and a 30-day staff-assigned in-stock freebie.
- Global 8:00 AM–11:59 PM Flash Polls. Voting grants community score, not spendable points. Student/resident rows remain hidden until at least three voters exist in that group.
- Campus and Barangay leaderboards are aggregate only; groups remain hidden until at least three members join.
- PIN-confirmed gifting: 1–20 direct points or one affordable in-stock product voucher, with a 50-point daily send cap. Product inventory is reserved when the voucher is sent so Cashier can honor it once.
- Role/channel native ads after every fifth post; time-limited in-app Flash Perch alerts; optional browser push.
- Cashier one-time voucher/freebie claims and loyalty QR/manual lookup. The digital purchase-card display uses existing paid POS spend, preventing duplicate transactions or rewards.

## Strong recommendations before public launch

1. Run a 30-day invite-only pilot with 20–50 people. Prove that moderation workload and repeat purchasing improve before opening a broad social network.
2. Assign a named moderator and response window. Check the queue at least twice daily; threats or exposed private data need an immediate escalation process.
3. Publish short Community Rules and a privacy notice reviewed for Philippine Data Privacy Act compliance. Define retention periods for reports, moderation notes, and inactive profiles.
4. Keep student verification in person. Do not collect ID photos unless counsel identifies a necessary purpose, documented retention period, and secure deletion process.
5. Do not describe self-declared barangay as identity verification. The interface labels it correctly until staff takes a justified verification action.
6. Keep community score separate from loyalty points, review gift/drop cost weekly, and add a monthly promotional budget ceiling before expanding rewards.
7. Do not filter ordinary criticism or political viewpoints. Phrase matches should only hold content for contextual review; record a reason for every removal.
8. Do not promise SMS OTP yet. Select a provider, verify sender/consent requirements, add OTP expiry and attempt limits, and design account recovery before replacing PIN login.
9. Treat Flash Perch as opt-in marketing. Limit frequency, show exact offer limits, prevent simultaneous over-claims, and honor valid displayed offers.
10. Back up the production database before deployment and on a schedule afterward. Test restore—not only backup creation.

## Optional Web Push setup

Create a VAPID key pair with a trusted local tool. Add these only in Render Environment settings:

- `WEBPUSH_VAPID_PUBLIC_KEY`
- `WEBPUSH_VAPID_PRIVATE_KEY`
- `WEBPUSH_VAPID_SUBJECT` such as `mailto:owner@example.com`

Never commit the private key. Without these variables, alerts still appear inside the app.

## Post-deployment acceptance test

1. Open `/healthz`; confirm `2026.09.03-community-v1`.
2. Log in as a loyalty customer, open `/community`, accept the optional terms, and create a Student test profile.
3. Submit a first post. Confirm it is pending and appears at `/admin/community`.
4. Publish it in Admin; verify it appears in Campus Hub and Town Square is read-only for that Student.
5. Create a Resident test account and verify the inverse permissions.
6. Schedule a Flash Poll for today and test one vote per account.
7. Send a point gift using the sender PIN; verify both ledgers. Send a product gift and redeem it once at Cashier; a second claim must fail.
8. At Cashier, scan or type a loyalty card number, record a paid sale, and confirm points/purchase-card progress update once.
9. Create an alert and a native ad. Verify targeting, expiry, impression count, and click count.
10. Submit reports from three different accounts. Confirm temporary quarantine and human resolution.

## Rollback

The schema change is additive. If application rollback is required, redeploy the previous commit; the new tables can remain without affecting older code. Do not delete tables or production records during rollback.
