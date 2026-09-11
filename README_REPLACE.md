# Macleen's Digital — CHAT Lite Camera Fix + Install Web App

This is an **incremental replacement package** for the latest Macleen's Hosted Apps uploader update.
Extract it into the project root (the folder containing `app.py`) and choose **Replace files in destination**.
Do not delete your database, `.env`, uploaded images, or unrelated project files.

## 1. CHAT Lite mobile camera-switch fix
The Flip Cam engine was changed for Android/Samsung devices that show:

`Cannot switch camera: Could not start video source`

The app now:
- detects available video-input devices after camera permission is granted;
- releases the current camera before trying to open the other camera (important on many Samsung/Android phones);
- prefers a different physical camera device when one is available;
- falls back to front/back `facingMode` requests;
- hot-swaps the new camera into active PeerJS calls;
- keeps screen sharing active if the user flips the camera while sharing a screen;
- tries to restore the previous camera if the flip fails;
- prevents repeated taps while a camera switch is already in progress.

## 2. Clickable “Install Web App” option
Customer-hosted app pages now have a **📲 Install Web App** button.
This applies to:
- CHAT Lite Per Use;
- CHAT Lite Lifetime Access;
- uploaded HTML apps with Free access;
- uploaded HTML apps with Per Use access;
- uploaded HTML apps with Lifetime Access.

The button installs the hosted page as a PWA / home-screen web app when the browser supports it. On iPhone/iPad and browsers that do not expose the automatic install prompt, the button shows the correct Add to Home Screen / Install App instructions.

**Important:** this does not give customers your HTML/ZIP source package. The installed web app still opens the protected Macleen's-hosted version and still follows the same access rules. A Per Use installation stops working after its paid 6-hour pass expires; Lifetime Access remains reopenable from the paid customer entitlement.

The PWA service worker intentionally does **not** cache protected app files, so installing the web app cannot bypass payment or expiry.

## 3. Uploaded-app browser permissions
The protected hosted-app viewer now also permits camera, microphone, screen-capture, clipboard, fullscreen, and downloads when the customer's browser/device permits them.

## Replace and deploy
After extracting these files over your latest project, run:

```bash
git status
git add .
git commit -m "Fix CHAT Lite camera switching and add web app install"
git push origin main
```

Then wait for Render to finish the deployment.
