# Menu Voting + Loyalty Card Printing Portal Update

This update builds on the latest Food House storefront/share/sub-size build.

## Public storefront

- Removed the public **Staff** button from the Food House storefront.
- Staff login still exists at `/staff/login` for direct access by staff.

## Menu Vote & Rankings restored

The Customer Portal now includes **Menu Vote & Rankings**.

- `Palabok` is restored as a default **Past Favorites** vote candidate.
- Current and past Product records are synchronized into the vote-candidate catalog.
- Short customer product suggestions can also become vote candidates.
- Each member may vote once per candidate per calendar month.
- The Customer Portal shows a live monthly Top 10 ranking and vote totals.
- Master Admin includes candidate controls and the monthly ranking.
- Old `menu_vote` rows are migrated into the new ranking system when the referenced Product still exists, so historical product votes are preserved where possible.

New additive tables:

- `menu_vote_candidate`
- `menu_preference_vote`

The old `menu_vote` table is retained for compatibility.

## Loyalty Rewards Card Printing Portal

Admin-only portal:

`/admin/loyalty-cards`

The portal:

- loads the customer's current name, member/card ID, points, expiration date, and Customer Portal profile photo;
- produces standard CR80/PVC-size previews (85.6 × 54 mm);
- prints a front and back card;
- creates a QR code that opens Rewards login with the customer's Card ID prefilled; the 4-digit PIN is still required;
- allows the card subtitle and visibility of photo/points/expiry/QR to be adjusted before printing;
- remembers the member's chosen base theme.

Five themes are included:

1. Classic Pink
2. Café Cream
3. Midnight Gold
4. Mint Fresh
5. Purple Craft

New additive Customer column:

- `card_theme`

## Phone/gallery profile photo upload

Customer Portal Account now accepts an image file from a phone or computer gallery:

- PNG
- JPG/JPEG
- WEBP
- GIF
- up to 2.5 MB

The image is stored in the database as a data URL so it survives Render restarts/deployments. The same saved image is automatically used by the Loyalty Card Printing portal.

Admin can also replace the member photo directly from the card-printing portal when necessary.

## Verification

Run:

```powershell
python scripts/predeploy_check.py
```

The source checker validates the storefront Staff-button removal, monthly Menu Voting/Palabok restoration, five-theme Loyalty Card Printing portal, phone/gallery profile photo upload, and the project's existing POS/Craft/AI Marketing/cash-flow safeguards.
