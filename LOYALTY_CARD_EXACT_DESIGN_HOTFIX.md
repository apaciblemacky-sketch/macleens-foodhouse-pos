# Loyalty Card Exact Design Hotfix

This hotfix corrects the Customer Portal preview and Admin print layout so they use the same approved landscape card renderer.

## Fixed
- Both card sides are landscape.
- Customer Portal preview is enlarged and responsive instead of being rendered at tiny physical CR80 screen size.
- Front layout now follows the approved arrangement:
  - Macleen's logo and heading at top-left
  - circular member photo below the heading
  - member name below the photo
  - Card ID and validity below the name
  - large QR panel on the right
  - SCAN TO LOGIN below the QR
  - fb.com/macleens along the bottom
- Back layout follows the approved arrangement:
  - logo + Macleen's Food House heading
  - LOYALTY REWARDS MEMBER subtitle
  - use-card / PIN / Customer Portal / return instructions
  - account-validity note
  - fb.com/macleens
- Removed all points-related content from the printed card itself, including point balance, earn-rate, point-value and minimum-redemption text.
- Customer Portal and Admin printing now include the same `_loyalty_card_renderer.html`, preventing preview/print design drift.
- Kept all five customer-selectable card themes.

## Validation completed
- Python source compilation passed.
- All 36 Jinja templates parsed successfully.
- Shared renderer data/layout checks passed.
- Full `scripts/predeploy_check.py` passed.
