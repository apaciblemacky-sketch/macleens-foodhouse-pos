# Student Modern Experience Update

This is a full replacement release. It preserves the existing Food House, Crafts,
Digital, loyalty, cash-flow, AI Marketing, cashier, and private investor features.

## Customer experience

- Mobile-first pink/teal visual system with compact navigation and accessible cards.
- Search and filters for available items, popular items, and budgets up to ₱20, ₱30, or ₱50.
- “Popular now” uses completed orders from the last 30 days; it is not a manual or fake label.
- Product cards show estimated preparation time, points earned, inventory urgency, and badges.
- Saved favorites for logged-in loyalty members.
- One-tap reorder from previous orders, revalidated against current products, prices, options, availability, and stock.
- Campus and class-break preferences for quicker pickup-time entry.
- Shareable Barkada carts. Friends add named selections; the organizer controls deletion and final submission.
- Private order tracking links with Submitted, Preparing, Ready, and Fulfilled stages.
- Modern toast feedback for storefront actions and existing no-refresh navigation/forms.

## Loyalty portal

- Visual milestone ring, login streak, and useful student missions.
- Favorites, Barkada carts, tracking, and Order Again are available in one dashboard.
- Existing promotions, points discounts, referrals, card customization, and product suggestions remain intact.

## Digital portal

- Responsive student-friendly catalog with search and modern cards.
- Seeded category structure only: School, Internship & Work, Personal Finance,
  Small Business, Productivity, and General.
- No products, prices, performance, or sales were invented.

## Operations and data safety

- Cashier can move accepted customer orders from Preparing to Ready to Handed Over.
- Admin can set a 1–180 minute product preparation estimate.
- Existing databases receive additive migrations for tracking, preferences, prep time,
  favorites support, and group ordering.
- Group checkout and reorder use the same server-side product, option, price, availability,
  and stock validation as normal checkout.
- Tracking URLs are random and do not show customer phone numbers or delivery addresses.

## Verification completed

- Python compile check.
- Full project pre-deploy check.
- Clean-database migration and startup.
- Storefront, loyalty, Digital, Admin, Cashier, payables, group-cart, and tracker renders.
- Favorite toggle, preferences, group item/submission, cashier fulfillment, and reorder flows.
- JavaScript syntax checks after rendering real Jinja data with apostrophes and quotes.
- ZIP structure and integrity check before delivery.
