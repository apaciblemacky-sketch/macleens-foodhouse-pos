#!/usr/bin/env python3
from pathlib import Path
import py_compile
from jinja2 import Environment
ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'templates'
app=(ROOT/'app.py').read_text(encoding='utf-8')
checks=[
'class DigitalCustomer(db.Model):',
"__bind_key__ = 'digital_accounts'",
"@app.route('/digital/account/login', methods=['GET', 'POST'])",
"@app.route('/digital/account/register', methods=['GET', 'POST'])",
"@app.route('/digital/account')",
"@app.route('/digital/item/<int:item_id>/trial/start', methods=['POST'])",
'Free Trial Users by App',
'digital_catalog_social_preview',
]
for marker in checks:
    source=app if marker!='Free Trial Users by App' else (T/'digital/admin.html').read_text(encoding='utf-8')
    if marker not in source: raise AssertionError('missing '+marker)
for name in ['digital/login.html','digital/register.html','digital/account.html','digital/base.html','digital/index.html','digital/apps/chat_lite.html']:
    if not (T/name).exists(): raise AssertionError('missing template '+name)
base=(T/'digital/base.html').read_text(encoding='utf-8')
for m in ['Install Digital App','digital_account_login','digital_account_home','data-pwa-autoprompt="1"']:
    if m not in base: raise AssertionError('Digital base missing '+m)
index=(T/'digital/index.html').read_text(encoding='utf-8')
for m in ['digital_catalog_share_image','og:image','summary_large_image']:
    if m not in index: raise AssertionError('Digital index missing '+m)
store=(T/'store_catalog.html').read_text(encoding='utf-8')
if 'data-pwa-key="macleens-foodhouse"' not in store: raise AssertionError('Storefront install prompt missing')
chat=(T/'digital/apps/chat_lite.html').read_text(encoding='utf-8')
for m in ['screen-share-ready','file-image-preview','NotAllowedError']:
    if m not in chat: raise AssertionError('CHAT Lite hotfix missing '+m)
js=(ROOT/'static/portal-pwa-install.js').read_text(encoding='utf-8')
for m in ['Install ', 'Not now', 'data-portal-install', 'mfh-pwa-install-dismissed']:
    if m not in js: raise AssertionError('PWA prompt JS missing '+m)

# Regression guard: Digital-only account ownership belongs to DigitalOrder, never Food Order.
order_block = app.split('class Order(db.Model):', 1)[1].split('class OrderItem(db.Model):', 1)[0]
digital_order_block = app.split('class DigitalOrder(db.Model):', 1)[1].split('class DigitalUsagePass(db.Model):', 1)[0]
if 'digital_customer_id = db.Column' in order_block:
    raise AssertionError('Food Order must not contain digital_customer_id')
if 'digital_customer_id = db.Column' not in digital_order_block:
    raise AssertionError('DigitalOrder must contain digital_customer_id')

py_compile.compile(str(ROOT/'app.py'),doraise=True)
env=Environment()
for t in T.rglob('*.html'): env.parse(t.read_text(encoding='utf-8'))
print('V41.1 DIGITAL ACCOUNTS + PWA + CHAT LITE SMOKE CHECK PASSED')
