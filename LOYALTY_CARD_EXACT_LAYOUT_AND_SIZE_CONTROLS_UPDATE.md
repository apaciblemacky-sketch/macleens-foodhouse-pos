# Loyalty Card Exact Layout + Element Size Controls Update

## What changed

- Replaced the previous loyalty-card preview with one **shared front/back renderer** used by both:
  - Customer Portal live preview
  - Admin Loyalty Card Printing Portal
- Rebuilt the landscape layout to follow the approved design:
  - Front: logo + MACLEEN'S heading, profile photo on the left, QR on the right, member name/Card ID/validity under the photo, SCAN TO LOGIN, and `fb.com/macleens`.
  - Back: Macleen's Food House header, member-use instructions, PIN reminder, portal reminder, return notice, validity note, and `fb.com/macleens`.
- Removed points/balance/reward-rate wording from the physical card design.
- Added per-member element-size controls in Admin:
  - Logo size
  - Profile photo size
  - QR size
  - Headings/member text size
  - Back information text size
- Element-size controls are print-safe and clamped to 80%–145%.
- Added Reset Sizes to 100%.
- Added screen-only Preview Zoom (80%–150%); it does not change the physical CR80 print size.
- Saved element sizes automatically appear in the customer's live portal preview.
- Added database columns for the five saved size controls; migrations are additive and preserve existing data.

## Shared files

- `templates/_loyalty_card_pair.html`
- `static/loyalty-card.css`

These two files are intentionally shared so customer preview and staff print output cannot drift into different layouts again.
