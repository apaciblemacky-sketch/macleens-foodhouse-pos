# Landscape Loyalty Card Preview Update

This update implements the approved loyalty card redesign.

## Included changes
- Changed the loyalty card print design to the approved **landscape** layout.
- Removed the **points display** from the printed loyalty card.
- Updated the **front card arrangement** to match the approved design:
  - Macleen's branding on the left
  - stacked "LOYALTY / REWARDS / MEMBER"
  - member photo block
  - member name, card ID, and validity
  - QR block on the right with "SCAN TO LOGIN"
- Updated the **back card arrangement** to match the approved design:
  - Macleen's Food House header
  - loyalty rules section
  - "If found, please return..." strip
  - validity note
  - `fb.com/macleens`
- Added **actual card preview** in the Customer Portal so customers can see the live front and back card design before staff prints it.
- Kept the **theme selection** behavior and made the preview update live when a different theme is chosen.

## Files changed
- `app.py`
- `templates/loyalty_card_portal.html`
- `templates/customer_dashboard.html`

## Notes
- Customer Portal previews now use the customer profile photo and login QR.
- The printed card no longer shows the customer's current point balance.
