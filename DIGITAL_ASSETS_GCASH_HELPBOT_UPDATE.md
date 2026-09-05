# Digital Assets, Gemini Help Bot & App Activation — v11

## Payment Flow: Manual GCash + Cashier Verification

Digital Business is deliberately set to **Manual GCash + cashier verification**.
The customer creates an order, follows your normal GCash payment instructions,
and waits for a cashier/admin to verify payment. There is no automatic payment
page redirect in this release.

After verification, a ready download unlocks automatically. Customers should
keep their private order page; it displays their download access code, delivery
instructions, and any app/activation details that you release.

## Protected Digital Asset Uploads

Open **Admin Control → Digital Business**. Each Digital offer can have one
protected downloadable asset. It is stored in the system, never in the public
`/static` folder, and is forced to download after payment.

- Allowed: PDF, DOCX, XLSX, CSV, images, ZIP packages, HTML, and other safe
  non-executable files.
- Not allowed: APK, EXE, MSI, BAT, CMD, DLL, PS1, and other installer/script
  formats. Do not distribute an Android installer through this portal.
- Default maximum: **20 MB**. `DIGITAL_ASSET_MAX_MB` can be set to 1–25 MB in
  Render only when the database/hosting plan can safely handle it.
- HTML is downloaded rather than run inside the Food House system.

Each order has an unguessable private link and a separate `MFH-...` download
access code. The access code protects the download only; it is **not**
automatically an app password. Existing orders retain the file version they
were originally assigned even if the catalog file is later replaced.

## Gemini-Powered Help Bot

The public Digital portal has clickable suggested questions plus a free-text
question box. Admin controls the final suggested questions and answers in
**Admin Control → Digital Business → Suggested AI Help Bot questions**.

1. In Render Environment, add `GEMINI_API_KEY` with your Gemini API key.
2. Restart/redeploy Render.
3. In Digital Admin, choose **Gemini only** or **Auto** as the Help Bot
   provider and save.
4. Write a customer question, click **Draft with Gemini**, review the answer,
   edit it if needed, then save it.

Gemini receives only the active Digital catalog and admin-prepared help
answers—never customer orders, GCash PINs, OTPs, download codes, or secret
keys. If Gemini is unavailable, the portal uses a labelled smart-help fallback
and offers the Facebook support handoff.

## One-Time App Activation Codes (2–3 Devices)

When creating or editing each Digital product, choose **Maximum app devices**:
no codes, 1, 2, or 3 devices. That product limit is copied to every new order,
so a later product change does not alter earlier buyers. After payment is
confirmed, the system issues one different `MFH-APP-...` code for each allowed
device. Admin can increase or reduce unused codes for one paid order when
needed; already activated devices are never silently removed. The customer sees
unused codes on their private paid order page; used codes become marked
Activated.

This is deliberately separate from the download access code and from an
optional manual license key/password entered by staff.

The 2–3 device limit becomes technically enforceable only when the digital app
or system calls these APIs on first use:

- `POST /api/digital/app/activate` with `activation_code`, a stable app-owned
  `device_id`, and optional `device_name`. It binds one code to one device and
  returns an activation token once.
- `POST /api/digital/app/validate` with that activation token and the same
  `device_id`. It confirms that the device remains authorized.

An offline HTML file, ZIP, APK, or copied folder cannot be device-limited by a
portal alone. If you sell an actual mobile app or hosted web system, build the
activation API into that product. For ordinary templates/files, use the
protected download code and clear license terms instead.

For account-specific, payment, refund, lost-code, or custom-project concerns,
the bot routes customers to:

`https://www.facebook.com/macleensdigital/`
