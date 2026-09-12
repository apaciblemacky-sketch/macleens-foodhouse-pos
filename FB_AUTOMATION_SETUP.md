# Facebook Page vs Group automation — separate connections

Macleen's intentionally keeps these as two independent channels/accounts.

## Facebook Page posting
Uses Meta Page Graph API credentials stored only in Render environment variables:
- `META_PAGE_ID`
- `META_PAGE_ACCESS_TOKEN`
- optional `META_GRAPH_VERSION`

The app posts the prepared daily menu to the Page `/feed` endpoint.

## Facebook Group posting
Do **not** put the Page token into the Group integration. The old official Meta Groups publishing API/permissions were retired. Macleen's therefore exposes a separate HTTPS bridge/provider integration:
- `FB_GROUP_POSTING_WEBHOOK_URL`
- optional `FB_GROUP_POSTING_WEBHOOK_TOKEN`

The bridge receives JSON containing the target group name/URL, prepared caption, date, and Food Store URL. Connect this only to an automation provider/account you are authorized to use for that Facebook Group.

In Admin → AI Marketing → Daily Facebook Menu Automation, enable Page posting and Group bridge independently.
