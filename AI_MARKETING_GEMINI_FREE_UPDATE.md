# Gemini Free AI Marketing Update

This update changes Macleen's AI Marketing so a paid OpenAI API account is no longer required.

## Added

- Gemini is now the default AI provider.
- Default model: `gemini-3.7-flash`.
- New Render secret: `GEMINI_API_KEY`.
- New Render setting: `GEMINI_MARKETING_MODEL`.
- AI Provider selector in `/admin/marketing`.
- Provider options: Gemini, Auto, OpenAI, and Smart Template.
- OpenAI remains optional and is no longer required for draft buttons to work.
- Built-in Smart Template fallback creates varied data-aware drafts when Gemini/OpenAI is unavailable or quota is exhausted.
- Marketing Memory now displays which engine/model made each draft.
- Group-assisted drafts work even without an external AI key because the Smart Template engine can take over.

## Free-first behavior

Default provider chain:

`Gemini Free -> Smart Template fallback`

Optional Auto provider chain:

`Gemini -> OpenAI -> Smart Template fallback`

The Smart Template fallback never calls an external AI service and therefore has no AI API charge.

## Privacy

Only summarized business/product/marketing data is sent to Gemini/OpenAI. Customer names, phone numbers, addresses, PINs, payment details, and individual customer records are not included in the AI marketing context.

## Setup

In Render Environment add:

`GEMINI_API_KEY = <your Google AI Studio key>`

`GEMINI_MARKETING_MODEL = gemini-3.7-flash`

Then redeploy, open `/admin/marketing`, leave **AI Provider = Gemini Free (Recommended)** and **Mode = Require Approval**, and click **Generate Marketing Draft**.
