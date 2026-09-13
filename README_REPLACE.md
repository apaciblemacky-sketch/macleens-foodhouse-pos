# Macleen's Digital v40 — 1-Day Trial + Protected Gemini Bridge

This is an incremental replacement update for the latest v39 + Render/admin-bootstrap + hosted-app local-storage build.

Replace only the files included in this ZIP. **Do not delete or reset the database.** Database setup adds the new trial/AI tables and hosted-app columns automatically.

## What changes

- Every existing and future **paid Hosted App** defaults to a 24-hour free trial.
- Trial starts only after the customer presses **Start Free Trial**.
- Active trial can be resumed until expiry; expired trial cannot normally be restarted on the same customer/browser.
- CHAT Lite also supports the 24-hour free trial.
- FREE hosted apps remain free and do not show a redundant trial.
- Lifetime ownership and paid per-use access remain unchanged.
- Admin Free Access remains unlimited.
- Optional **Macleen's Gemini Bridge** per hosted app.
- The Gemini API key remains on Render/server only and is never placed in uploaded HTML, PWA manifests, or customer browser code.
- AI-enabled uploaded apps use `window.MacleensAI.generate(prompt)`.
- Trial AI requests and Paid/Admin daily AI requests are capped per app with admin-editable limits.
- Existing secure hosted-app sandbox and device-local storage bridge are preserved.

## Render requirement for Gemini-enabled apps

Keep your existing secret environment variable:

`GEMINI_API_KEY`

(or `GOOGLE_API_KEY`).

Optional: `GEMINI_HOSTED_APP_MODEL`.

## Deploy

```bash
git status
git add .
git commit -m "Add 1-day hosted app trials and secure Gemini bridge"
git push origin main
```

Expected release marker:

`2026.09.13-digital-trial-gemini-v40`
