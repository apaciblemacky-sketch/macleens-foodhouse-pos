# Macleen's Security + Auto-Hosted HTML + Android Screen Share Handling Update

Incremental update for the current Macleen's project. Extract into the project root and replace existing files. No database reset is required.

## 1. Protected HTML upload -> Hosted App automatically
- A single `.html` / `.htm` file uploaded through **Digital Admin -> Add digital offer + protected file** is automatically promoted to a Hosted App.
- A `.zip` containing `index.html` is also automatically promoted.
- The app receives its separate PWA identity, current per-use hours, optional Lifetime price, and uploaded web-app icon.
- **Admin Free Launch** is automatically available for these promoted apps.
- Non-HTML files stay normal protected downloads.

## 2. CHAT Lite screen sharing on Android
- Current Android/iOS mobile browsers generally do not expose the web `getDisplayMedia()` Screen Capture API.
- The button now detects unsupported mobile browsers and explains that screen sharing requires a supported desktop browser instead of silently failing.
- Desktop screen sharing remains enabled, and the server sends a `Permissions-Policy` allowing `display-capture` for the same origin.
- Camera, microphone, chat, files, and video calls remain available on supported mobile browsers.

## 3. Staff security hardening
New/changed staff credentials:
- Username: 8-20 alphanumeric characters.
- Password: 8-20 alphanumeric characters, with at least one uppercase, one lowercase, and one number.
- Common, repeated, and obvious sequential passwords are blocked.
- Existing legacy credentials are not erased. After a valid login, a legacy short/non-compliant account is forced through a secure credential upgrade before privileged access continues.

Additional controls:
- Memory-hard scrypt password hashing for new/changed staff passwords.
- Old password hashes automatically rehash after a successful compliant login.
- Persistent login throttling by privacy-preserving client-IP hash.
- Progressive temporary blocks after repeated failures.
- Generic login failure messages to reduce username discovery.
- Small randomized failed-login delay against rapid guessing.
- CSRF protection for staff login and credential changes.
- Admin must re-enter their current Admin password before changing any staff credentials.
- Staff sessions remain non-persistent and retain the existing inactivity timeout.
- Staff sessions are bound to the browser User-Agent fingerprint.
- Admin/staff pages are marked no-store/no-cache.
- Security headers: HSTS in production, nosniff, same-origin framing, strict referrer policy, and browser Permissions Policy.
- New production databases no longer silently create predictable `1234` / `1111` bootstrap PINs. Configure `DEFAULT_ADMIN_PASSWORD` and `DEFAULT_CASHIER_PASSWORD` if a production database has no staff accounts yet.

## Important security note
The requested 8-20 alphanumeric-only password policy is implemented exactly, but OWASP currently recommends allowing longer passwords/passphrases and a much higher maximum length. The added hashing, throttling, CSRF, re-authentication, session, and header protections substantially harden the system, but no web application can be guaranteed "unhackable."
