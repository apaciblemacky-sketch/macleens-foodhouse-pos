#!/usr/bin/env python3
"""Behavioral checks for protected Digital Business assets and support flow."""
from __future__ import annotations

import io
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='mfh-digital-assets-v10-') as folder:
        db_path = (Path(folder) / 'digital-assets.db').resolve().as_posix()
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        os.environ['SECRET_KEY'] = 'digital-assets-smoke-check'
        os.environ.pop('PAYMONGO_SECRET_KEY', None)

        import app as m

        m.app.config.update(TESTING=True)
        with m.app.app_context():
            m.db.create_all()
            m.run_schema_migrations()
            asset = m.DigitalAssetFile(
                original_filename='budget-tracker.html', download_filename='budget-tracker.html',
                content_type='text/html', file_size=31,
                sha256=m.hashlib.sha256(b'<h1>Tracker</h1>').hexdigest(),
                file_data=b'<h1>Tracker</h1>', uploaded_by='admin',
            )
            m.db.session.add(asset)
            m.db.session.flush()
            item = m.DigitalItem(
                name='Budget Tracker', category_name='Personal Finance', product_type='DOWNLOAD',
                price=49, cost=0, asset_file_id=asset.id, file_format='HTML', is_active=True,
            )
            m.db.session.add(item)
            m.db.session.flush()
            order = m.DigitalOrder(
                item_id=item.id, customer_name='Digital Tester', contact_number='09981234567',
                email='tester@example.com', quantity=1, unit_price=49, unit_cost=0,
                total_price=49, payment_method='GCASH', asset_file_id=asset.id,
                delivery_access_code='MFH-SMOKETEST', status='PENDING_PAYMENT', payment_status='PENDING',
            )
            m.db.session.add(order)
            m.db.session.flush()
            m.create_main_digital_order(order)
            m.digital_mark_order_paid(order)
            assert order.status == 'READY' and m.digital_order_can_download(order)

            # Exercise the hosted GCash adapter without making a network call.
            gateway_order = m.DigitalOrder(
                item_id=item.id, customer_name='Gateway Tester', contact_number='09987654321',
                email='gateway@example.com', quantity=2, unit_price=49, unit_cost=0,
                total_price=98, payment_method='GCASH', asset_file_id=asset.id,
                delivery_access_code='MFH-GATEWAY', status='PENDING_PAYMENT', payment_status='PENDING',
            )
            m.db.session.add(gateway_order)
            m.db.session.flush()
            m.create_main_digital_order(gateway_order)
            class FakeResponse:
                def __init__(self, payload, status_code=200):
                    self._payload = payload; self.status_code = status_code; self.ok = status_code < 300; self.content = b'{}'; self.text = ''
                def json(self):
                    return self._payload
            original_post, original_get = m.requests.post, m.requests.get
            try:
                os.environ['PAYMONGO_SECRET_KEY'] = 'sk_test_smoke_only'
                captured_checkout = {}
                def fake_checkout_post(*args, **kwargs):
                    captured_checkout.update(kwargs.get('json') or {})
                    return FakeResponse({'data': {'id': 'cs_smoke', 'attributes': {'checkout_url': 'https://checkout.paymongo.test/session'}}})
                m.requests.post = fake_checkout_post
                with m.app.test_request_context('/'):
                    checkout_url = m.digital_create_paymongo_checkout(gateway_order)
                assert checkout_url == 'https://checkout.paymongo.test/session' and gateway_order.payment_gateway == 'PAYMONGO'
                line_item = captured_checkout['data']['attributes']['line_items'][0]
                assert line_item['amount'] == 4900 and line_item['quantity'] == 2
                m.requests.get = lambda *args, **kwargs: FakeResponse({'data': {'attributes': {'payment_intent': {'attributes': {'status': 'succeeded'}}}}})
                assert m.digital_check_paymongo_payment(gateway_order)
                assert gateway_order.payment_status == 'PAID' and gateway_order.status == 'READY'
                assert gateway_order.main_order.status == 'COMPLETED' and gateway_order.main_order.payment_verified
            finally:
                m.requests.post, m.requests.get = original_post, original_get
                os.environ.pop('PAYMONGO_SECRET_KEY', None)

            m.save_digital_setting('digital_support_bot_provider', 'TEMPLATE')
            m.db.session.commit()

            client = m.app.test_client()
            with client.session_transaction() as browser:
                browser['admin_user'] = 'admin'
                browser['_staff_last_activity'] = datetime.now().isoformat()

            status_page = client.get(f'/digital/order/{order.tracking_token}')
            assert status_page.status_code == 200
            assert b'Your protected download is ready' in status_page.data
            item_page = client.get(f'/digital/item/{item.id}')
            assert item_page.status_code == 200 and b'Protected download' in item_page.data
            blocked = client.post(f'/digital/order/{order.tracking_token}/download', data={'access_code': 'WRONG'})
            assert blocked.status_code == 302
            download = client.post(f'/digital/order/{order.tracking_token}/download', data={'access_code': 'MFH-SMOKETEST'})
            assert download.status_code == 200 and download.data == b'<h1>Tracker</h1>'
            assert download.headers.get('X-Content-Type-Options') == 'nosniff'

            bot = client.post('/api/digital-support-bot', json={'question': 'How can I download a paid file?'})
            assert bot.status_code == 200
            bot_data = bot.get_json()
            assert bot_data['success'] and 'facebook.com/macleensdigital' in bot_data['support_url']

            response = client.post(
                '/admin/digital/item/save',
                data={
                    'name': 'Spreadsheet Pack', 'category_name': 'General', 'product_type': 'DOWNLOAD',
                    'price': '25', 'cost': '0', 'file_format': 'XLSX', 'turnaround_days': '0',
                    'is_active': '1', 'asset_file': (io.BytesIO(b'example workbook bytes'), 'spreadsheet-pack.xlsx'),
                },
                content_type='multipart/form-data',
            )
            assert response.status_code == 302
            uploaded_item = m.DigitalItem.query.filter_by(name='Spreadsheet Pack').first()
            assert uploaded_item and uploaded_item.asset_file and uploaded_item.asset_file.file_data == b'example workbook bytes'

            # A normal Digital order creates the linked cashier transaction; a
            # cashier/admin acceptance must unlock the attached ready download.
            storefront_order_response = client.post(
                f'/digital/item/{item.id}',
                data={'customer_name': 'Cashier Sync', 'contact_number': '09980000000', 'email': 'sync@example.com', 'quantity': '1', 'payment_method': 'GCASH', 'gcash_ref': '123456'},
            )
            assert storefront_order_response.status_code == 302
            storefront_order = m.DigitalOrder.query.filter_by(email='sync@example.com').first()
            assert storefront_order and storefront_order.main_order_id and storefront_order.asset_file_id == asset.id
            cashier_accept = client.post(f'/pos/verify/{storefront_order.main_order_id}', data={'action': 'ACCEPT'})
            assert cashier_accept.status_code == 302
            m.db.session.expire_all()
            storefront_order = m.db.session.get(m.DigitalOrder, storefront_order.id)
            assert storefront_order.payment_status == 'PAID' and storefront_order.status == 'READY'

            try:
                with m.app.test_request_context('/'):
                    from werkzeug.datastructures import FileStorage
                    m.digital_asset_from_upload(FileStorage(stream=io.BytesIO(b'no'), filename='unsafe.exe', content_type='application/octet-stream'))
                raise AssertionError('Executable digital asset was incorrectly accepted')
            except m.OrderValidationError:
                pass

            admin_page = client.get('/admin/digital')
            assert admin_page.status_code == 200
            assert b'protected digital asset' in admin_page.data.lower()

    print('DIGITAL ASSETS, GATEWAY-READY CHECKOUT, AND SUPPORT BOT V10 SMOKE CHECK PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
