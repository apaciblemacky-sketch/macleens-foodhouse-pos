# Macleen's Digital — Hosted Apps Uploader + Admin Free Access

This is an incremental replacement package for the latest Macleen's project.
Extract the ZIP into the project root (the folder containing `app.py`) and choose **Replace files in destination**.
Do not delete your database, `.env`, uploaded images, or unrelated project files.

## New Hosted HTML Apps manager
Digital Admin now includes **Hosted HTML Apps**.

You can:
- upload one `.html` file, or a `.zip` containing `index.html`;
- choose customer access: **Free**, **Pay Per Use**, **Lifetime**, or **Per Use + Lifetime**;
- set per-use and lifetime prices;
- feature/hide the app;
- replace the app package later without another Git deployment;
- keep existing paid/lifetime customer access pointing to the current hosted version;
- launch every uploaded hosted app **FREE as Admin**, regardless of its customer pricing.

## Admin Free Access
Admin launch is protected by the existing Macleen's admin login. It does not create an order, payment, or usage pass.
Each uploaded app card in Digital Admin has **Launch Free as Admin**.
CHAT Lite keeps its existing free admin route/button too.

## Per-use behavior
Paid per-use access remains resumable for up to 6 hours. Closing the browser, losing internet, refreshing, or a PC power interruption does not automatically consume the pass. The customer can deliberately choose **End Usage** to finish it early.

## Storage / hosting
Uploaded app packages are stored in the Digital database-backed asset storage, not only on Render's temporary filesystem. After this platform update is deployed, adding or replacing compatible hosted apps does not require Git or a Render redeploy.

## Static-app safety limits
This uploader is for static browser apps: HTML, CSS, JavaScript, images, audio, fonts, and similar assets.
ZIPs must contain `index.html`; unsafe paths, symlinks, encrypted entries, and oversized expanded bundles are rejected.
Uploaded apps run in a sandbox so they cannot use Macleen's admin session. Apps that require server-side Python/Flask, Node/PHP, Macleen's authenticated APIs, or browser capabilities restricted by the sandbox may still need manual integration.

## Deploy this platform update once
After replacing the files, run:

```bash
git status
git add .
git commit -m "Add hosted HTML app uploader and admin free access"
git push origin main
```

Then wait for the connected Render service to finish the new deployment.
