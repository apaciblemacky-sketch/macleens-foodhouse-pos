# Macleen's Ulam Voting

Server-backed daily Ulam voting portal for Macleen's Food House.

## Render service

The repository's `render.yaml` now defines a second Node.js web service named `macleens-ulam-voting`.

- Root directory: `ulam-voting`
- Build: `npm install`
- Start: `npm start`
- Health: `/healthz`

## Required Render environment variables

Set these on the Ulam Voting service:

- `DATABASE_URL` — use the same PostgreSQL connection URL as the existing Food House service if you want both systems on the same database.
- `ADMIN_PIN` — change this from the demo value before opening the portal to customers.
- `JWT_SECRET` — Render generates this automatically from the Blueprint.
- `ANALYZE_URL` — optional server-side AI endpoint accepting POST `{ ranking, voters }` and returning `{ text }`.
- `AI_API_KEY` — optional secret sent as a Bearer token to `ANALYZE_URL`; it never appears in the browser.

If `ANALYZE_URL` is empty or unavailable, the server uses a built-in local analysis.

## Data safety

The voting service creates only tables prefixed with `ulam_voting_`. It does not reset, delete, or alter the existing Food House customer/order/product tables.

The current implementation intentionally keeps voting-member accounts separate until the existing member schema is explicitly mapped. This avoids accidentally changing the live POS/customer data.

## Voting rules enforced by the server

- Asia/Manila voting window: 6:00 PM through 12:00 NN the next day.
- Cycle date is the date the round opened at 6:00 PM.
- One submission per member per cycle.
- Maximum 10 selected ulams.
- Duplicate ulam selections are rejected.
- Public results are blocked while voting is open; admin can see live results.
- Suggestions require member login and are limited to 60 characters.
- Admin-only ulam, suggestion, analysis, and menu actions.
- Saved menu selections must come from the current cycle's top 10 and can only be saved after voting closes.

## Existing system integration

The safest first deployment is to share the existing PostgreSQL database through `DATABASE_URL` while keeping the Ulam tables isolated. After the existing member table/schema is reviewed, the member login can be mapped to it without touching order/customer records.
