# Customer Suggestions + Loyalty Card Theme Update

## Simplified customer feedback
- Menu Vote & Rankings is removed from the Customer Portal.
- The related ranking/candidate panel and monthly vote metric are removed from the active Master Admin UI.
- **What would you like to buy from our shop?** is the single customer product-request feature.
- Customer entries remain literal free-text words in Admin and are not converted into products, catalog entries, or vote candidates.
- Repeated wording can still be grouped in Admin only as a demand signal.
- Legacy vote tables/data are preserved non-destructively; the old vote endpoint now redirects to the suggestion box instead of recording a vote.

## Customer-controlled loyalty card theme
Members can choose any of the five existing card themes directly in Customer Portal: Classic Pink, Café Cream, Midnight Gold, Mint Fresh, or Purple Craft.

The selected theme saves to `customer.card_theme`, so the Admin Loyalty Card Printing Portal automatically uses the member's chosen design. Customer phone/gallery profile-photo upload remains available and feeds the printed card.

## Printed card
The CR80/PVC front-and-back card now includes **fb.com/macleens** and its copy no longer refers to menu voting.
