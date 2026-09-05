# Digital Assets, GCash Checkout & Help Bot — v10

## Protected Digital Asset Uploads

Open **Admin Control → Digital Business**.

Each Digital offer can now have one protected downloadable asset. Upload a file
while creating or editing an offer. The file is stored in the system and is
never placed in the public `/static` folder.

- Allowed: PDF, DOCX, XLSX, CSV, images, ZIP files, HTML files, and other
  non-executable digital assets.
- Not allowed: installers and executable/script files such as EXE, APK, MSI,
  BAT, CMD, DLL, or PS1. Package source/project files as a ZIP instead.
- Default maximum upload: **20 MB**. Adjust `DIGITAL_ASSET_MAX_MB` in Render
  only if the database and hosting plan can safely handle a larger value. The
  system permits 1–25 MB.
- HTML is supplied as a forced download. It is not run or hosted inside the
  Food House system, which protects customers from active content.

When an offer's file is replaced, existing orders keep the file version that
was attached when they ordered. New orders receive the replacement file.

## Paid Download and Access Code

Every Digital order receives a private tracking link and a unique `MFH-...`
access code.

1. Customer submits an order.
2. Cashier verifies manual Cash/GCash payment, or the online gateway verifies
   GCash payment.
3. A ready downloadable product unlocks automatically.
4. The private order page displays the access code.
5. Customer enters that code to download the file.

Both the private tracking link and the access code are needed. The system
forces the file to download instead of opening it in the browser. It records
downloads and limits each order to five by default. An Admin can reset an
order's access code if it was exposed or the customer needs a new one.

## GCash Payment Setup

Manual GCash + cashier verification is the safe default and works immediately.

For hosted online GCash checkout, the system is prepared for **PayMongo**:

1. Open/activate a PayMongo merchant account and enable GCash.
2. In Render → your service → Environment, add `PAYMONGO_SECRET_KEY` with the
   server secret from PayMongo. Never put it in the Admin page, source code, or
   a public post.
3. Set `PUBLIC_BASE_URL=https://macleens-foodhouse-pos.onrender.com` in Render
   if it is not already set.
4. Deploy this update.
5. In **Admin Control → Digital Business**, choose **PayMongo hosted GCash
   checkout** and save.
6. Make a small real/test GCash payment. The customer returns to the private
   order page, where the system verifies the checkout server-to-server before
   releasing the download.

If a customer closes the payment page before returning, they can tap **Check
GCash payment** on their private order page, or staff can verify the linked
cashier order. Keep Manual mode selected until PayMongo has approved the
merchant account and the key is in Render.

## Digital Help Bot and Facebook Handoff

The Digital portal now has a help panel. It answers catalog, download, GCash,
and custom-work questions, but never asks for GCash PINs, OTPs, payment
passwords, or download codes.

Its support handoff is fixed to:

`https://www.facebook.com/macleensdigital/`

The bot uses Gemini or OpenAI only when the existing matching environment key
is configured. Without an AI key it still supplies safe built-in answers and
the Facebook handoff. Choose the provider in **Admin Control → Digital
Business → GCash & Help Bot settings**.
