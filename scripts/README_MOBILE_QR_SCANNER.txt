MACLEEN'S MOBILE QR SCANNER PATCH
=================================

WHAT THIS PATCH DOES
--------------------
Use a smartphone as a wireless loyalty-card QR scanner while the laptop stays
on the Cashier POS. The phone sends a short-lived selected member to the open
Cashier POS under the SAME staff username. The laptop selects the member by
itself without refreshing the page.

IMPORTANT SAFETY RULE
---------------------
The phone never creates an order and never gives points. Record the sale only
once on the laptop Cashier POS. This prevents duplicate sales, receipts, stock
deductions, BIR records, and loyalty points.

INSTALL
-------
1. Extract this ZIP into your current Macleen's project folder.
2. Allow Windows to replace the files with the same names.
3. Do NOT replace your database file. This ZIP contains no database file.
4. Start the project using your normal RUN_MACLEENS.bat. The existing run and
   deploy scripts already run the included verification script automatically.
5. When you are ready, run your normal DEPLOY_TO_RENDER.bat to deploy it.

HOW TO USE IT
-------------
1. On the laptop, sign in to Cashier POS and keep /pos/cashier open.
2. On the phone, open:
   https://YOUR-RENDER-URL/pos/mobile-scanner
3. Sign in on the phone with the SAME cashier/admin username that is open on
   the laptop.
4. Tap Start camera scanner, scan the customer's 2x2 loyalty QR, then tap
   Send member to laptop Cashier POS.
5. In about two seconds, the laptop Counter Tray changes to Registered Member
   and displays the selected customer. Continue and complete the sale there.

NOTES
-----
- Camera QR scanning needs an HTTPS page plus Chrome or Edge on Android with
  camera permission. Manual card-number/QR-link entry is included as a backup.
- A sent selection expires after two minutes and a newer scan replaces an old
  unclaimed one. This avoids attaching the wrong customer to a later sale.
- The new mobile_loyalty_scan table is created automatically at application
  startup. No manual database migration is needed.

FILES IN THIS PATCH
-------------------
- app.py
- templates/cashier_pos.html
- templates/mobile_scanner.html
- scripts/loyalty_card_delivery_v12_smoke_check.py
- scripts/predeploy_check.py
