# Points Discount and Meta Insights Update

## Loyalty points discount

- Cashier can apply member points to the current POS purchase.
- Cashier can apply points to a linked completed purchase from the last 24 hours.
- Customers can apply points during storefront checkout.
- Customers can apply points to eligible recent purchases from their dashboard.
- Minimum redemption remains 20 points and 1 point equals PHP 1.
- The system prevents double redemption, recalculates base points on the net paid amount, and restores points when an order is cancelled or reverted.
- A completed purchase shows the refund/change due when points are applied after payment.

## AI Marketing Meta insights

- Posted marketing entries now accept aggregate Meta results: reach, impressions, reactions, comments, shares, saves, link clicks, new followers, optional ad spend, and notes.
- Saved insights can be analyzed with the configured Gemini or OpenAI provider.
- If the configured AI is unavailable, the system provides a local smart-template analysis.
- The analysis uses the post caption, aggregate metrics, and up to ten earlier posts with saved insights for internal comparison.
- No Facebook login, access token, customer names, phone numbers, addresses, PINs, or individual-user Meta data is required.

## Running locally

Double-click `RUN_MACLEENS.bat`. It checks dependencies, runs the existing pre-deployment validation, opens the local site, and starts the Flask application.

## Deployment

Upload or replace the complete project contents, preserving your production database and environment variables. The additive database migration runs automatically when the updated application starts.
