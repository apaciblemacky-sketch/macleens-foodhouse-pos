# Macleen's AI Marketing Integration

This update adds an AI marketing control center at:

`/admin/marketing`

It combines two workflows:

1. **Facebook Page** — AI drafts posts and, when authorized, the system can publish them through Meta's Page API.
2. **Joined Facebook Groups** — AI prepares a group-specific caption + verified Macleen's link, then the admin uses **Copy Post** + **Open Group** and posts manually. The system intentionally does not automate a personal Facebook account or joined-group posting.

## What the AI reads

The AI receives only business context prepared by the server:

- current active Food House products and stock;
- Food House completed-sales quantities/revenue for the past 30 days;
- active public promotions;
- active Craft items, availability, stock, likes, views and order counts;
- Featured / Top Seller flags;
- recent AI Marketing history;
- the configured business scope, cooldown and posting rules;
- a saved Facebook Group's tone/rule notes when creating a group-assisted draft.

It is instructed to vary the purpose and wording from day to day and may choose to **skip** a day instead of forcing a weak post.

## Server-side safeguards

Python remains in control even when `AUTO_PUBLISH` is selected:

- inactive and out-of-stock items are rejected;
- public/member-only promotion boundaries are preserved;
- peso amounts in AI captions must match an approved current product/promo price;
- same-product cooldown is enforced;
- allowed posting hours are enforced;
- max-posts-per-day is enforced;
- target weekly cadence is converted into a minimum time gap;
- groups can never be API-published by this module.

## Render environment variables

Add these to the existing `macleens-foodhouse-pos` Render Web Service:

- `OPENAI_API_KEY` — your OpenAI API key.
- `OPENAI_MARKETING_MODEL` — defaults to `gpt-5.5`; change this later without changing code if desired.
- `META_APP_ID` — Facebook/Meta Developer App ID.
- `META_APP_SECRET` — Facebook/Meta Developer App secret.
- `META_GRAPH_VERSION` — defaults to `v25.0` in this build.
- `MARKETING_CRON_TOKEN` — create a long random secret value.
- `PUBLIC_BASE_URL` — `https://macleens-foodhouse-pos.onrender.com` (replace with your custom domain later if you add one).
- `SECRET_KEY` — keep your existing stable secret. The Facebook Page token is encrypted using this key, so changing `SECRET_KEY` later requires reconnecting the Page.

Do not put any API key/token in GitHub.

## Meta/Facebook app setup

Create or use a Meta Developer app and configure Facebook Login for the production website.

Requested Page permissions in the connection flow:

- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`

The OAuth callback URL used by this system is:

`https://macleens-foodhouse-pos.onrender.com/admin/marketing/facebook/callback`

If you later use a `.com` domain, set `PUBLIC_BASE_URL` and add the equivalent callback URL to the Meta app.

In Admin → AI Marketing, click **Connect Facebook Page**, authorize Meta, then select the Page returned by your account. Page access tokens are encrypted before being stored in the application database.

Depending on your Meta app mode, roles and requested permissions, Meta may require app review/business verification before non-test users can authorize the integration.

## OpenAI setup

The AI writer uses OpenAI's Responses API with strict JSON-schema output. The API key is read only from `OPENAI_API_KEY`; it is never rendered into a page or saved to the database.

Recommended first mode: **Require Approval**. Generate/review posts for several days before enabling **Fully Automatic**.

## UptimeRobot / scheduler

The protected endpoint is:

`https://macleens-foodhouse-pos.onrender.com/tasks/marketing/run`

Preferred request header:

`Authorization: Bearer YOUR_MARKETING_CRON_TOKEN`

For a service that cannot send a custom Authorization header, the endpoint also accepts:

`https://macleens-foodhouse-pos.onrender.com/tasks/marketing/run?token=YOUR_MARKETING_CRON_TOKEN`

The endpoint can be checked hourly. It does **not** publish every time it is called. It first evaluates whether AI Marketing is enabled, the current Philippine time is in the allowed window, the weekly cadence is due, and the daily post cap has not been reached.

Keep your ordinary UptimeRobot `/healthz` monitor separate from the marketing trigger.

## Admin workflow

- **Draft Only** — creates draft/history only.
- **Require Approval** — recommended starting mode; AI drafts, you review/edit and click Post to FB.
- **Fully Automatic** — when the scheduler says a post is due, AI selects the business/post purpose and publishes a validated draft to the connected Facebook Page.

The Marketing Memory table stores the decision type, selected item, AI reason, caption, status, link, model, Meta post ID/error, and timestamps so future AI context can avoid repetitive posting.

## Facebook Groups

Save each group with its:

- name and URL;
- Food House / Crafts / Both scope;
- preferred post types;
- cooldown days;
- rules/tone notes.

Then click **AI Draft**, review the generated copy, **Copy Post**, **Open Group**, paste it into Facebook, and click **Mark Posted** in Macleen's. Marking it posted updates the group's cooldown and AI marketing history.
