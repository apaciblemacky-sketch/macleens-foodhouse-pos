#!/usr/bin/env python3
"""Static smoke checks for the September 2026 business/admin upgrade.

This check intentionally avoids importing Flask so it can catch missing files,
old wording, or accidental rollback before the full runtime smoke suite starts.
"""
from pathlib import Path
import py_compile
from jinja2 import Environment, TemplateSyntaxError

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / 'templates'
source = (ROOT / 'app.py').read_text(encoding='utf-8')

def need(text, marker, label):
    if marker not in text:
        raise AssertionError(f'{label}: missing {marker!r}')

def absent(text, marker, label):
    if marker in text:
        raise AssertionError(f'{label}: retired marker is still present: {marker!r}')

# Core server-side feature markers.
for marker in [
    'class ManualDailySalesRecord(db.Model):',
    'class WebsiteVisitDaily(db.Model):',
    "@app.route('/admin/api/website-analytics')",
    "@app.route('/admin/api/website-analytics/ai-suggestion', methods=['POST'])",
    'if not validate_staff_csrf():',
    'def render_digital_social_preview(item):',
    "@app.route('/social/digital/<int:item_id>/<version>.jpg')",
    "'Rent': ('EXPENSE', 'Rent')",
    "'Electricity': ('EXPENSE', 'Electricity')",
    "'Water': ('EXPENSE', 'Water')",
    'FINANCIAL_OPTIONAL_EXPENSE_ACCOUNTS',
    'def financial_product_catalog(period_start, period_end):',
    "financial_vault_drop_sales_percent",
    "financial_vault_drop_cost_percent",
    'def portal_about(portal):',
    'def facebook_group_bridge_ready():',
    'FB_GROUP_POSTING_WEBHOOK_URL',
    'META_PAGE_ACCESS_TOKEN',
    'support_create_paypal_checkout',
]:
    need(source, marker, 'app.py')

# Daily Sales Record is daily, with a separate blank/manual input.
bir = (T / 'bir_sales_record.html').read_text(encoding='utf-8')
for marker in ['INTERNAL DAILY SALES RECORD', 'System Daily Sales', 'Blank / Manual Daily Sales Record', 'Receipt / reference', 'Include in Financial Statements']:
    need(bir, marker, 'Daily Sales Record')
absent(bir, '<th>Order</th>', 'Daily Sales Record should not be transaction-first')

# Financial Statements controls.
fin = (T / 'financial_statements.html').read_text(encoding='utf-8')
for marker in ['Products & Cost', 'Vault Drop — Sales %', 'Vault Drop — Cost %', 'Report Settings & Expense Checklist', 'Selling Price', 'Sales %', 'Cost %']:
    need(fin, marker, 'Financial Statements')

# Digital social cards mirror the product-link preview pattern.
digital_item = (T / 'digital' / 'item.html').read_text(encoding='utf-8')
for marker in ['property="og:image"', 'property="og:image:type" content="image/jpeg"', 'property="og:image:width" content="1200"', 'property="og:image:height" content="630"', 'twitter:card', 'Share product']:
    need(digital_item, marker, 'Digital social preview')

# Independent About + analytics sections.
store = (T / 'store_catalog.html').read_text(encoding='utf-8')
craft_public = (T / 'craft' / 'index.html').read_text(encoding='utf-8')
digital_public = (T / 'digital' / 'index.html').read_text(encoding='utf-8')
for text, name in [(store, 'Storefront'), (craft_public, 'Crafts'), (digital_public, 'Digital')]:
    need(text, "{% include '_portal_about.html' %}", f'{name} About')
need(craft_public, 'Pickup and delivery available', 'Crafts fulfillment header')
absent(craft_public, 'Unique Visitors', 'Crafts public visitor counters')
absent(craft_public, 'Total Visits', 'Crafts public visitor counters')

analytics = (T / '_website_analytics_panel.html').read_text(encoding='utf-8')
for marker in ['Visits & Unique Visitors', 'data-analytics-days', 'data-analytics-metric', 'AI suggestion', "'X-CSRF-Token':root.dataset.csrf"]:
    need(analytics, marker, 'Interactive analytics')

# Page and Group posting remain separate credential paths.
marketing = (T / 'marketing_admin.html').read_text(encoding='utf-8')
for marker in ['Automatically publish Page menu', 'Send to separate Facebook Group automation bridge', 'FB_GROUP_POSTING_WEBHOOK_URL', 'Facebook Page credentials are never reused for Group posting']:
    need(marketing, marker, 'Facebook automation preparation')

# Cashier promo buttons are gone from the top while old-record compatibility can remain server-side.
cashier = (T / 'cashier_pos.html').read_text(encoding='utf-8')
absent(cashier, '<button onclick="openPromoModal(', 'Cashier top promotions')
need(cashier, 'macleens-shared.css', 'Cashier shared stylesheet foundation')
need(store, 'macleens-shared.css', 'Storefront shared stylesheet foundation')

# Safer project hygiene.
gitignore = (ROOT / '.gitignore').read_text(encoding='utf-8')
for marker in ['instance/*.db', '*.db-wal', '*.db-shm', '*.zip']:
    need(gitignore, marker, '.gitignore')
if not (ROOT / 'scripts' / 'backup_database.py').exists():
    raise AssertionError('Safe database backup script is missing.')

deploy = (ROOT / 'DEPLOY_TO_RENDER.bat').read_text(encoding='utf-8')
for marker in ['backup_database.py', 'predeploy_check.py', 'v39_business_upgrade_smoke_check.py']:
    need(deploy, marker, 'Deployment workflow')

# Compile Python and parse all HTML/Jinja templates.
py_compile.compile(str(ROOT / 'app.py'), doraise=True)
py_compile.compile(str(ROOT / 'marketing_agent.py'), doraise=True)
env = Environment()
for template in sorted(T.rglob('*.html')):
    try:
        env.parse(template.read_text(encoding='utf-8'))
    except TemplateSyntaxError as exc:
        raise AssertionError(f'Jinja syntax error in {template.relative_to(ROOT)}:{exc.lineno}: {exc.message}') from exc

print('V39 BUSINESS/FINANCE/ANALYTICS/SOCIAL UPGRADE SMOKE CHECK PASSED')
