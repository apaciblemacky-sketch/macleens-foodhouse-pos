# Macleen's Digital — 1-Day Trials + Protected Gemini Bridge

## Customer trial behavior

- Every **paid Hosted App** defaults to a **24-hour free trial**.
- The trial starts only when the customer presses **Start Free Trial**; simply viewing the product does not start the clock.
- The same active trial can be reopened until its expiry.
- A customer/account or the same browser cannot normally start that app's trial a second time after it expires.
- Apps that are already **FREE** do not show a redundant trial.
- Ordinary downloadable files are not trialed because releasing the source/file would defeat protected delivery.
- Admin Free Access remains unlimited and separate from customer trials.

## Gemini security model

Enable **This app needs Gemini AI** in Digital Admin for a hosted app that needs AI.

The customer's HTML never receives `GEMINI_API_KEY` or `GOOGLE_API_KEY`. The uploaded app talks to the protected parent viewer, the viewer calls Macleen's server, and Macleen's server calls Gemini.

The server uses the existing Render secret:

- `GEMINI_API_KEY`, or
- `GOOGLE_API_KEY`

Optional model override:

- `GEMINI_HOSTED_APP_MODEL`

If the override is not set, the system falls back to the existing Digital/Marketing Gemini model setting.

## HTML API for hosted apps

When Gemini Bridge is enabled, Macleen's automatically injects a safe browser helper:

```javascript
const result = await window.MacleensAI.generate(
  "Give me three practical ways to reduce this month's expenses."
);
console.log(result.text);
console.log(result.remaining);
```

There is **no API key** in this code. `result.remaining` shows the remaining AI-call allowance for that access window/day.

A defensive example:

```javascript
async function askAI(prompt) {
  if (!window.MacleensAI?.available) {
    throw new Error('AI is not enabled for this hosted app.');
  }
  const result = await window.MacleensAI.generate(prompt);
  return result.text;
}
```

## Usage controls

Digital Admin has two limits for each AI-enabled hosted app:

- **Trial AI requests** — default 25 total during that trial.
- **Paid/Admin AI requests per day** — default 100 per entitled access/day.

These limits protect the owner's Gemini quota from accidental loops or abuse. They can be edited per app.

## Privacy note

AI prompts are relayed to Google Gemini for processing. The Gemini secret key remains server-side. The bridge does not give uploaded apps access to Macleen's admin session, customer database, payment credentials, or other hosted apps' data.
