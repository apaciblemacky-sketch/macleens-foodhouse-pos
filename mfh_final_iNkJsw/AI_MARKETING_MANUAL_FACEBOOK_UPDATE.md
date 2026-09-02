# AI Marketing — Manual Facebook Posting Update

This update removes the Meta Developer / Facebook Graph API connection from Macleen's AI Marketing.

## What changed

- No `META_APP_ID`, `META_APP_SECRET`, or Facebook OAuth setup is required.
- Macleen's does not log into Facebook and does not store a Facebook access token.
- Any legacy stored Meta Page token is disabled and cleared during database setup.
- AI-generated Facebook Page drafts use a manual workflow: **Edit → Copy Post → Open Page → Paste/Post → Mark Posted**.
- Joined Facebook Groups use the same assisted/manual workflow.
- The optional scheduler can create drafts when due, but it can never publish to Facebook.
- Marketing memory/cooldowns still work because `Mark Posted` records the posting date.
- Gemini remains the default AI provider; the built-in Smart Template engine remains the no-API fallback.
- Default Gemini model is `gemini-3.5-flash-lite`; a Render environment override still takes priority.

## Render environment

Needed for Gemini:

- `GEMINI_API_KEY`
- `GEMINI_MARKETING_MODEL=gemini-3.5-flash-lite`
- `PUBLIC_BASE_URL=https://macleens-foodhouse-pos.onrender.com`

Optional:

- `MARKETING_CRON_TOKEN` for scheduled draft creation
- `OPENAI_API_KEY` / `OPENAI_MARKETING_MODEL` only if OpenAI fallback is desired

The old Meta environment variables can be deleted from Render if they were added.

## Admin workflow

Open `/admin/marketing`. Save the Facebook Page name/link as a shortcut. Generate a draft, edit it if needed, click **Copy Post**, click **Open Page**, paste/publish it in Facebook, then return to Macleen's and click **Mark Posted**.
