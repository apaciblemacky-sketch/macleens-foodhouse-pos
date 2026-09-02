# Macleen's AI Marketing Integration — Gemini Free Default

The AI Marketing control center is available at:

`/admin/marketing`

It combines two workflows:

1. **Facebook Page** — marketing drafts can be created by Gemini, OpenAI (optional), or the built-in Smart Template engine. When Meta is authorized, the system can publish approved/automatic posts to the connected Facebook Page.
2. **Joined Facebook Groups** — the system prepares a group-specific caption + verified Macleen's link, then the admin uses **Copy Post** + **Open Group** and posts manually. The system does not automate a personal Facebook account or joined-group posting.

## AI provider order

The Admin now has an **AI Provider** selector:

- **Gemini Free (Recommended)** — default. Uses `GEMINI_API_KEY` and `GEMINI_MARKETING_MODEL` (default `gemini-3.7-flash`). If Gemini is unavailable or quota is exhausted, the system automatically falls back to the built-in Smart Template engine.
- **Auto: Gemini → OpenAI → Template** — tries Gemini first, then OpenAI if configured, then the local Smart Template fallback.
- **OpenAI (Optional)** — uses the existing OpenAI integration when `OPENAI_API_KEY` is configured, with Smart Template fallback if unavailable.
- **Smart Template — No API** — makes varied, data-aware drafts locally without any external AI request.

Google currently lists a free tier for Gemini API with free input/output tokens on supported models, subject to limits. Free-tier content may be used by Google to improve its products. See: https://ai.google.dev/gemini-api/docs/pricing

## Privacy boundary

External AI providers receive only business context prepared by the server:

- active Food House products, prices, stock and 30-day aggregate sales;
- active public promotions;
- Craft items, availability, stock, likes, views and order counts;
- Featured / Top Seller flags;
- recent marketing history;
- configured business scope, cooldown and posting rules;
- a saved Facebook Group's tone/rule notes when making a group-assisted draft.

The marketing context does **not** include customer names, phone numbers, addresses, PINs, payment references, passwords, or individual order/customer records.

## Server-side safeguards

Python remains in control even when `AUTO_PUBLISH` is selected:

- inactive and out-of-stock items are rejected;
- public/member-only promotion boundaries are preserved;
- peso amounts in generated captions must match an approved current product/promo price;
- same-product cooldown is enforced;
- allowed posting hours are enforced;
- max-posts-per-day is enforced;
- target weekly cadence is converted into a minimum time gap;
- Facebook Groups can never be API-published by this module.

## Render environment variables

Recommended free setup:

- `GEMINI_API_KEY` — create in Google AI Studio and keep only in Render Environment.
- `GEMINI_MARKETING_MODEL` — default `gemini-3.7-flash`.
- `META_APP_ID` — Facebook/Meta Developer App ID.
- `META_APP_SECRET` — Facebook/Meta Developer App secret.
- `META_GRAPH_VERSION` — defaults to `v25.0` in this build.
- `MARKETING_CRON_TOKEN` — long random secret.
- `PUBLIC_BASE_URL` — `https://macleens-foodhouse-pos.onrender.com`.
- `SECRET_KEY` — keep the existing stable secret.

Optional only:

- `OPENAI_API_KEY`
- `OPENAI_MARKETING_MODEL`

Do not put any API key/token in GitHub or client-side JavaScript.

## Gemini setup

Create a Gemini API key in Google AI Studio:

https://aistudio.google.com/apikey

All new Google AI Studio keys are currently created as authorization keys. Google recommends keeping `GEMINI_API_KEY` server-side. The Macleen's integration sends it only from Flask/Render to the Gemini API using the `x-goog-api-key` header.

After adding the key to Render, open **Admin → AI Marketing**, leave **AI Provider = Gemini Free (Recommended)** and **Mode = Require Approval**, then click **Generate Marketing Draft**.

If Gemini cannot be reached, the draft still works using **Smart Template fallback**, and the Marketing Memory row shows `smart-template-fallback` as the engine.

## Meta/Facebook app setup

Create or use a Meta Developer app and configure Facebook Login for the production website.

Requested Page permissions:

- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`

OAuth callback:

`https://macleens-foodhouse-pos.onrender.com/admin/marketing/facebook/callback`

In Admin → AI Marketing, click **Connect Facebook Page**, authorize Meta, then select the Page returned by your account. Page access tokens are encrypted before being stored in the application database.

Depending on Meta app mode, roles and requested permissions, Meta may require app review/business verification before non-test users can authorize the integration.

## UptimeRobot / scheduler

Protected endpoint:

`https://macleens-foodhouse-pos.onrender.com/tasks/marketing/run`

Preferred request header:

`Authorization: Bearer YOUR_MARKETING_CRON_TOKEN`

Fallback query-token form:

`https://macleens-foodhouse-pos.onrender.com/tasks/marketing/run?token=YOUR_MARKETING_CRON_TOKEN`

The endpoint can be checked hourly. It does **not** publish every time it is called. It first checks whether AI Marketing is enabled, current Philippine time is in the allowed window, weekly cadence is due, and the daily post cap has not been reached.

Keep the ordinary UptimeRobot `/healthz` monitor separate.

## Recommended first workflow

Use **Require Approval** first. Generate and review several posts before switching to **Fully Automatic**.

The Marketing Memory table stores the selected engine/model, decision type, selected item, reason, caption, status, link, Meta post ID/error, and timestamps so future decisions can avoid repetition.


---

## Current Facebook mode (supersedes the Meta API sections above)

The current build intentionally uses **manual Facebook posting**. Meta Developer OAuth/API publishing has been removed. Use `/admin/marketing` to generate/edit/copy drafts, open the saved Facebook Page or Group, post manually, and click **Mark Posted**. See `AI_MARKETING_MANUAL_FACEBOOK_UPDATE.md`.
