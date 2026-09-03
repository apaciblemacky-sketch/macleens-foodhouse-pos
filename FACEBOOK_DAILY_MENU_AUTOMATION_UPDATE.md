# Facebook Daily Menu Automation Update

## What is included

- Automatic daily Facebook Page menu posts through Meta's official Graph API.
- Approval-first mode, which is enabled by default to prevent accidental posts.
- A protected hourly scheduler endpoint with one-successful-send-per-day protection.
- Messenger webhook verification and signed-event validation.
- Automatic current-menu reply when a customer messages `MENU`, `ULAM`, or `PRICE LIST`.
- Storefront **Get menu in Messenger** link using the configured Page username.
- Messenger sent, delivered, read, clicked, and failed logs.
- A tracked full-menu link in Messenger replies.
- Optional webhook handoff to an approved Meta technology provider for paid,
  proactive messages to people whose Meta opt-ins are managed by that provider.

The system does not bulk-message Facebook followers or loyalty members. A normal
Messenger reply is sent only after the person contacts the Page. Proactive daily
marketing messages require a compliant provider and valid Meta opt-ins.

## Render environment values

Open the Render service, choose **Environment**, and add:

- `META_PAGE_ID` — the numeric Facebook Page ID.
- `META_PAGE_ACCESS_TOKEN` — a Page access token with the required Page posting
  and messaging permissions. The Meta app normally needs `pages_manage_posts`
  for Page publishing and `pages_messaging` for Messenger replies; Meta may also
  require `pages_read_engagement` during Page/token setup.
- `META_WEBHOOK_VERIFY_TOKEN` — a long random phrase you choose. Enter this same
  value when configuring the Meta webhook.
- `META_APP_SECRET` — the Meta App Secret used to verify signed webhook events.
- `META_GRAPH_VERSION` — defaults to `v24.0`; update it in Render when Meta asks
  the app to move to a newer supported version.

Optional paid-provider values:

- `META_MARKETING_PROVIDER_WEBHOOK_URL`
- `META_MARKETING_PROVIDER_TOKEN`

Never paste access tokens into Admin fields, source code, GitHub, screenshots, or
the deployment script.

## Meta webhook

Use this callback URL in the Meta App dashboard:

`https://macleens-foodhouse-pos.onrender.com/meta/messenger/webhook`

Use the exact same value from `META_WEBHOOK_VERIFY_TOKEN` as the verification
token. Subscribe the app/Page to `messages`, `messaging_postbacks`,
`message_deliveries`, `message_reads`, and `messaging_referrals` when those
fields are available to the app. Complete the required Meta App Review and put
the app in Live mode before serving customers who are not app testers.

## Daily scheduler

Call the following URL hourly using a scheduler. Replace the sample token with
the existing Render `MARKETING_CRON_TOKEN` value:

`https://macleens-foodhouse-pos.onrender.com/tasks/facebook-menu/run?token=YOUR_MARKETING_CRON_TOKEN`

The endpoint uses Philippine time, waits until the time saved in AI Marketing,
and will not duplicate a successful Page/provider send for the same day.

## Admin workflow

1. Open `/admin/marketing`.
2. Find **Daily Facebook Menu Automation**.
3. Save the Page username and daily time.
4. Keep **Require approval before sending** enabled during initial testing.
5. Use **Refresh Today's Draft** and verify products and prices.
6. Use **Publish to Facebook Page Now** for the first live test.
7. Test the storefront Messenger link and send `MENU` to the Page.
8. After successful testing, optionally disable approval and enable automatic
   Page publishing.

## Storefront and Admin repairs in this release

- The hero logo is substantially larger on desktop and mobile.
- The buttons below the storefront search bar were removed.
- Search initializes correctly after no-refresh navigation and brings matching
  products directly below the search box with a live result count.
- Add Product now handles database failures cleanly, returns to the correct Admin
  section, and highlights the newly created product so the result is visible.
- The shared no-refresh layer now carries viewport settings between portal pages
  and ignores repeat clicks while a request is already running.
