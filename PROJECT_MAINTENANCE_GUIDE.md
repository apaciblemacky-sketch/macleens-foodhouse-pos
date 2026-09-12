# Macleen's maintenance & safer deployment guide

## Before every Git push
1. Close any local process actively writing to the SQLite database when practical.
2. Run `python scripts/backup_database.py`.
3. Run `python scripts/predeploy_check.py`.
4. Review `git status` and make sure no database, `.env`, customer export, or backup is staged.
5. Use a descriptive commit message, for example: `Improve daily sales, analytics and Facebook automation`.
6. Push `main` only after the checks pass.

On Windows, `scripts/DEPLOY_TO_RENDER.bat` performs this flow for you.

## Database safety
The live/local SQLite database is `instance/foodhouse_pos.db`. It is excluded from Git. Backups created by the helper go to `../macleens_backups/` by default, outside the repository. Never send a project ZIP that contains `instance/*.db`, SQLite `-wal`/`-shm` sidecars, `.env`, payment secrets, or customer exports.

If production uses Render PostgreSQL through `DATABASE_URL`, use the database provider's backup/snapshot feature. A local SQLite backup does not back up PostgreSQL.

## Gradual app.py split
Do not split the 16k+ line file all at once. A safe sequence is:
1. Shared utility/services (analytics, social previews, payments) with no routes.
2. Digital Blueprint/routes.
3. Crafts Blueprint/routes.
4. Marketing Blueprint/routes.
5. Financial/admin Blueprint/routes.
6. Storefront/POS last because it is the highest-traffic operational path.

Move one area at a time and run the pre-deploy checks after every move. This update already keeps AI marketing/analytics helper logic in `marketing_agent.py` and moves new shared UI styles into `static/macleens-shared.css`, which is the beginning of that cleanup rather than a risky full rewrite.

## Inline-style cleanup
Do it gradually. New reusable About and Analytics components use `static/macleens-shared.css`. For future UI changes, add a named class there instead of another `style="..."` attribute. Refactor the Cashier POS and Food Storefront in small visual sections so behavior does not change unexpectedly.
