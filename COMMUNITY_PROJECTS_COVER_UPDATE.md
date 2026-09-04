# Macleen’s Community Projects & Cover Photos v7

Release: `2026.09.04-community-project-cover-v7`

## What changed

- The Main Admin profile is now role-neutral. Campus, Department, Graduating
  Year, Vibe, Barangay, and Resident-since fields are cleared and never shown.
- The Campus category “Textbook Buy / Sell / Swap” is now “Buy & Sell,” and a
  separate “Discussions” category was added.
- A word-only post can tag up to 25 eligible people. Tags remain restricted to
  the member’s authorized community, with the Main Admin available to both.
- Profile settings now accept a JPG, PNG, or WEBP cover photo up to 5 MB. The
  server verifies the image, corrects phone orientation, crops it to 1600×600,
  and compresses it to WEBP before saving it. Members may remove it anytime.
- Internal group chat is removed from the customer and Admin interfaces. Old
  message tables are retained only to make the upgrade non-destructive, and the
  old message API returns HTTP 410.
- Workspaces are now presented as project monitoring. Each workspace shows a
  live completion percentage plus Total, In Progress, Completed, and Overdue
  task counts. Tasks, shared notes, polls, invitations, and member controls all
  update without refreshing the page.
- A workspace owner may add an optional Facebook Messenger group URL for
  conversation outside the Community.

## Strong recommendations

1. Keep the 25-tag ceiling. Unlimited tagging would quickly become a spam and
   notification-abuse problem.
2. Keep cover uploads normalized. Saving original phone photos in the database
   would make backups and page loads grow too quickly.
3. Use project workspaces for outcomes and accountability—not sensitive files.
   Keep student IDs, payment information, grades, and private addresses out.
4. Continue using Facebook Messenger for real-time conversation rather than
   rebuilding chat and constant polling inside this beta.
5. Move the production database to managed PostgreSQL before a large launch.
   If cover-photo use grows substantially, move the compressed images to proper
   object storage and store only their URLs in the database.

## Verification

1. Run `RUN_MACLEENS.bat` and wait for every check to pass.
2. Open Community Settings, upload a cover photo, save, and open the profile.
3. View `@uzu.macky`; only the Main Admin role should appear—no school or
   resident demographic boxes.
4. Create a Campus post and confirm Buy & Sell and Discussions are available.
5. Add multiple tags with “Add @tag” and confirm the page does not refresh.
6. Open Projects, create a workspace, assign a task, and move it to Doing and
   Done. Confirm the progress card changes immediately.
7. Confirm no internal chat composer appears. If a Messenger URL was added,
   confirm its external link opens correctly.
8. After deployment, open `/healthz` and confirm the release string above.
