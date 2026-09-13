# Macleen's Hosted App Local Storage Bridge Hotfix

Replace only:

- `templates/digital/apps/hosted_app_viewer.html`

This keeps uploaded apps sandboxed, but gives compatible apps a namespaced device-local storage bridge through the trusted viewer. It does not expose admin/customer cookies or server data.

After deploying, upload `budget-tracker-macleens-compatible.html` as the replacement version of the Budget Tracker hosted app.
