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
    with tempfile.TemporaryDirectory(prefix='mfh-digital-assets-v12-') as folder:
        db_path = (Path(folder) / 'digital-assets.db').resolve().as_posix()
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        os.environ['SECRET_KEY'] = 'digital-assets-smoke-check'
        os.environ.pop('PAYMONGO_SECRET_KEY', None)
        os.environ.pop('PAYPAL_CLIENT_ID', None)
        os.environ.pop('PAYPAL_CLIENT_SECRET', None)
        os.environ.pop('PAYPAL_MODE', None)

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
                price=49, cost=0, asset_file_id=asset.id, file_format='HTML', app_device_limit=2, is_active=True,
            )
            m.db.session.add(item)
            m.db.session.flush()
            faq = m.DigitalSupportFAQ(
                question='How do I use my access code?',
                answer='Use it only on your private paid order page to unlock the download.',
                is_active=True, sort_order=10,
            )
            m.db.session.add(faq)
            order = m.DigitalOrder(
                item_id=item.id, customer_name='Digital Tester', contact_number='09981234567',
                email='tester@example.com', quantity=1, unit_price=49, unit_cost=0,
                total_price=49, payment_method='QRPH', asset_file_id=asset.id,
                delivery_access_code='MFH-SMOKETEST', status='PENDING_PAYMENT', payment_status='PENDING',
            )
            m.db.session.add(order)
            m.db.session.flush()
            m.create_main_digital_order(order)
            m.digital_mark_order_paid(order)
            assert order.status == 'READY' and m.digital_order_can_download(order)

            # Exercise the hosted QR Ph adapter without making a network call.
            gateway_order = m.DigitalOrder(
                item_id=item.id, customer_name='Gateway Tester', contact_number='09987654321',
                email='gateway@example.com', quantity=2, unit_price=49, unit_cost=0,
                total_price=98, payment_method='QRPH', asset_file_id=asset.id,
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
                    captured_checkout['url'] = args[0]
                    return FakeResponse({'data': {'id': 'cs_smoke', 'attributes': {'checkout_url': 'https://checkout.paymongo.test/session'}}})
                m.requests.post = fake_checkout_post
                with m.app.test_request_context('/'):
                    checkout_url = m.digital_create_paymongo_checkout(gateway_order)
                assert checkout_url == 'https://checkout.paymongo.test/session' and gateway_order.payment_gateway == 'PAYMONGO'
                assert captured_checkout['url'].endswith('/v2/checkout_sessions')
                line_item = captured_checkout['data']['attributes']['line_items'][0]
                assert line_item['amount'] == 4900 and line_item['quantity'] == 2
                assert captured_checkout['data']['attributes']['reference_number'] == f'MFH-DIGITAL-{gateway_order.id}'
                assert captured_checkout['data']['attributes']['payment_method_types'] == ['qrph']
                m.requests.get = lambda *args, **kwargs: FakeResponse({'data': {'attributes': {'payment_intent': {'attributes': {'status': 'succeeded'}}}}})
                assert m.digital_check_paymongo_payment(gateway_order)
                assert gateway_order.payment_status == 'PAID' and gateway_order.status == 'READY'
                assert gateway_order.main_order.status == 'COMPLETED' and gateway_order.main_order.payment_verified
            finally:
                m.requests.post, m.requests.get = original_post, original_get
                os.environ.pop('PAYMONGO_SECRET_KEY', None)

            # PayPal is a separate server-verified Digital checkout route.
            # Its approval page never releases the file by itself: the server
            # fetches and captures the exact stored PayPal order first.
            paypal_order = m.DigitalOrder(
                item_id=item.id, customer_name='PayPal Tester', contact_number='09985555555',
                email='paypal@example.com', quantity=1, unit_price=49, unit_cost=0,
                total_price=49, payment_method='PAYPAL', asset_file_id=asset.id,
                delivery_access_code='MFH-PAYPAL', status='PENDING_PAYMENT', payment_status='PENDING',
            )
            m.db.session.add(paypal_order)
            m.db.session.flush()
            m.create_main_digital_order(paypal_order)
            paypal_values = {}
            def paypal_payload(status, approve=False):
                body = {
                    'id': 'PAYPAL-SMOKE-ORDER', 'status': status,
                    'purchase_units': [{
                        'reference_id': paypal_values.get('reference_id', f'MFH-DIGITAL-{paypal_order.id}'),
                        'custom_id': paypal_values.get('custom_id', str(paypal_order.id)),
                        'amount': {'currency_code': 'PHP', 'value': paypal_values.get('value', '49.00')},
                    }],
                }
                if approve:
                    body['links'] = [{'rel': 'approve', 'href': 'https://www.sandbox.paypal.com/checkoutnow?token=PAYPAL-SMOKE-ORDER'}]
                return body
            def fake_paypal_post(url, *args, **kwargs):
                if url.endswith('/v1/oauth2/token'):
                    return FakeResponse({'access_token': 'paypal-access-token-for-smoke'})
                if url.endswith('/v2/checkout/orders'):
                    unit = kwargs['json']['purchase_units'][0]
                    paypal_values.update({key: unit[key] for key in ('reference_id', 'custom_id')})
                    paypal_values['value'] = unit['amount']['value']
                    return FakeResponse(paypal_payload('CREATED', approve=True))
                if url.endswith('/capture'):
                    return FakeResponse(paypal_payload('COMPLETED'))
                raise AssertionError(f'Unexpected PayPal POST: {url}')
            try:
                os.environ['PAYPAL_CLIENT_ID'] = 'paypal-smoke-client'
                os.environ['PAYPAL_CLIENT_SECRET'] = 'paypal-smoke-secret'
                os.environ['PAYPAL_MODE'] = 'sandbox'
                m.requests.post = fake_paypal_post
                with m.app.test_request_context('/'):
                    paypal_url = m.digital_create_paypal_checkout(paypal_order)
                assert paypal_url.startswith('https://www.sandbox.paypal.com/') and paypal_order.payment_gateway == 'PAYPAL'
                m.requests.get = lambda *args, **kwargs: FakeResponse(paypal_payload('APPROVED'))
                assert m.digital_check_paypal_payment(paypal_order)
                assert paypal_order.payment_status == 'PAID' and paypal_order.status == 'READY'
                assert paypal_order.main_order.status == 'COMPLETED' and paypal_order.main_order.payment_verified
            finally:
                m.requests.post, m.requests.get = original_post, original_get
                os.environ.pop('PAYPAL_CLIENT_ID', None)
                os.environ.pop('PAYPAL_CLIENT_SECRET', None)
                os.environ.pop('PAYPAL_MODE', None)

            m.save_digital_setting('digital_support_bot_provider', 'TEMPLATE')
            m.db.session.commit()

            client = m.app.test_client()
            with client.session_transaction() as browser:
                browser['admin_user'] = 'admin'
                browser['_staff_last_activity'] = datetime.now().isoformat()

            # Digital Business offers Secure Checkout (QRPH) and optional
            # PayPal. Food House payment methods stay separate.
            os.environ['PAYMONGO_SECRET_KEY'] = 'sk_test_payment_settings'
            os.environ['PAYPAL_CLIENT_ID'] = 'paypal-settings-client'
            os.environ['PAYPAL_CLIENT_SECRET'] = 'paypal-settings-secret'
            os.environ['PAYPAL_MODE'] = 'sandbox'
            settings_saved = client.post('/admin/digital/payment-settings', data={
                'bot_provider': 'TEMPLATE', 'support_url': m.DIGITAL_SUPPORT_FACEBOOK_DEFAULT, 'paypal_enabled': '1',
            })
            assert settings_saved.status_code == 302
            settings = m.digital_payment_settings()
            assert settings['gateway_mode'] == 'PAYMONGO' and settings['paymongo_active']
            assert settings['paypal_enabled'] and settings['paypal_available']
            enabled_item_page = client.get(f'/digital/item/{item.id}')
            assert enabled_item_page.status_code == 200
            assert b'Secure Checkout' in enabled_item_page.data and b'PayPal' in enabled_item_page.data
            assert b'PayMongo' not in enabled_item_page.data and b'GCash' not in enabled_item_page.data
            assert b'<select name="payment_method"' in enabled_item_page.data

            # A tampered/manual payment choice is rejected and does not leave
            # a pending cashier-verification order behind.
            blocked_manual = client.post(
                f'/digital/item/{item.id}',
                data={'customer_name': 'Blocked Manual', 'contact_number': '09981111111', 'email': 'manual@example.com', 'quantity': '1', 'payment_method': 'GCASH'},
            )
            assert blocked_manual.status_code == 302
            assert not m.DigitalOrder.query.filter_by(email='manual@example.com').first()

            # A checkout-start failure rolls back both Digital and sales rows;
            # it cannot fall back to a cashier-verification order.
            def fake_failed_checkout_post(*args, **kwargs):
                return FakeResponse({'errors': [{'detail': 'Gateway unavailable'}]}, status_code=503)
            m.requests.post = fake_failed_checkout_post
            try:
                failed_checkout = client.post(
                    f'/digital/item/{item.id}',
                    data={'customer_name': 'Failed Checkout', 'contact_number': '09982222222', 'email': 'failed@example.com', 'quantity': '1', 'payment_method': 'QRPH'},
                )
            finally:
                m.requests.post = original_post
            assert failed_checkout.status_code == 302
            assert not m.DigitalOrder.query.filter_by(email='failed@example.com').first()

            status_page = client.get(f'/digital/order/{order.tracking_token}')
            assert status_page.status_code == 200
            assert b'Your protected download is ready' in status_page.data
            assert b'not automatically an app password' in status_page.data
            item_page = client.get(f'/digital/item/{item.id}')
            assert item_page.status_code == 200 and b'Protected download' in item_page.data
            blocked = client.post(f'/digital/order/{order.tracking_token}/download', data={'access_code': 'WRONG'})
            assert blocked.status_code == 302
            download = client.post(f'/digital/order/{order.tracking_token}/download', data={'access_code': 'MFH-SMOKETEST'})
            assert download.status_code == 200 and download.data == b'<h1>Tracker</h1>'
            assert download.headers.get('X-Content-Type-Options') == 'nosniff'

            # Replacing a protected product file must not strand already-paid
            # customers. The same private token and claim code download the
            # new release; activation/device limits are intentionally untouched.
            update = client.post(
                '/admin/digital/item/save',
                data={
                    'item_id': str(item.id), 'name': item.name, 'category_name': item.category_name,
                    'product_type': item.product_type, 'price': str(item.price), 'cost': str(item.cost or 0),
                    'file_format': 'HTML', 'turnaround_days': '0', 'app_device_limit': '2',
                    'is_active': '1', 'asset_release_notes': 'Added the updated dashboard and corrected formulas.',
                    'asset_file': (io.BytesIO(b'<h1>Tracker v2</h1>'), 'budget-tracker-v2.html'),
                },
                content_type='multipart/form-data',
            )
            assert update.status_code == 302
            m.db.session.expire_all()
            item = m.db.session.get(m.DigitalItem, item.id)
            order = m.db.session.get(m.DigitalOrder, order.id)
            assert item.asset_version == 2 and order.download_count == 0
            assert m.digital_order_download_asset(order).file_data == b'<h1>Tracker v2</h1>'
            updated_page = client.get(f'/digital/order/{order.tracking_token}')
            assert updated_page.status_code == 200 and b"What's updated in version 2" in updated_page.data
            updated_download = client.post(f'/digital/order/{order.tracking_token}/download', data={'access_code': 'MFH-SMOKETEST'})
            assert updated_download.status_code == 200 and updated_download.data == b'<h1>Tracker v2</h1>'

            bot = client.post('/api/digital-support-bot', json={'question': 'How do I use my access code?'})
            assert bot.status_code == 200
            bot_data = bot.get_json()
            assert bot_data['success'] and bot_data['model'] == 'prepared-answer' and 'facebook.com/macleensdigital' in bot_data['support_url']
            draft = client.post('/admin/digital/support-faq/ai-draft', json={'question': 'Can I use this on more than one device?'})
            assert draft.status_code == 200 and draft.get_json()['success'] and draft.get_json()['answer']
            added_faq = client.post('/admin/digital/support-faq/save', data={
                'question': 'Where can I get support?', 'answer': 'Message Macleen’s Digital on Facebook for order-specific support.',
                'sort_order': '20', 'is_active': '1',
            })
            assert added_faq.status_code == 302 and m.DigitalSupportFAQ.query.filter_by(question='Where can I get support?').first()

            response = client.post(
                '/admin/digital/item/save',
                data={
                    'name': 'Spreadsheet Pack', 'category_name': 'General', 'product_type': 'DOWNLOAD',
                    'price': '25', 'cost': '0', 'file_format': 'XLSX', 'turnaround_days': '0',
                    'delivery_instructions': 'Open the included START-HERE file after downloading.',
                    'app_device_limit': '3',
                    'is_active': '1', 'asset_file': (io.BytesIO(b'example workbook bytes'), 'spreadsheet-pack.xlsx'),
                },
                content_type='multipart/form-data',
            )
            assert response.status_code == 302
            uploaded_item = m.DigitalItem.query.filter_by(name='Spreadsheet Pack').first()
            assert uploaded_item and uploaded_item.asset_file and uploaded_item.asset_file.file_data == b'example workbook bytes'
            assert uploaded_item.delivery_instructions.startswith('Open the included') and uploaded_item.app_device_limit == 3

            # A normal public order can only use Secure Checkout. The server
            # confirmation immediately marks both records paid/ready; a
            # cashier acceptance is neither shown nor required.
            def fake_public_checkout_post(*args, **kwargs):
                return FakeResponse({'data': {'id': 'cs_public_smoke', 'attributes': {'checkout_url': 'https://checkout.example.test/public'}}})
            m.requests.post = fake_public_checkout_post
            try:
                secure_order_response = client.post(
                    f'/digital/item/{item.id}',
                    data={'customer_name': 'Secure Checkout', 'contact_number': '09980000000', 'email': 'secure@example.com', 'quantity': '1', 'payment_method': 'QRPH'},
                )
            finally:
                m.requests.post = original_post
            assert secure_order_response.status_code == 302 and secure_order_response.headers['Location'] == 'https://checkout.example.test/public'
            secure_order = m.DigitalOrder.query.filter_by(email='secure@example.com').first()
            assert secure_order and secure_order.main_order_id and secure_order.asset_file_id == item.asset_file_id and secure_order.activation_device_limit == 2
            assert secure_order.main_order.status == 'SECURE_PAYMENT'
            assert not m.Order.query.filter_by(id=secure_order.main_order_id, status='VERIFICATION').first()
            # Even an old direct cashier URL cannot force this gateway order
            # into a paid state before server-side confirmation.
            blocked_cashier = client.post(f'/pos/verify/{secure_order.main_order_id}', data={'action': 'ACCEPT'})
            assert blocked_cashier.status_code == 302
            m.db.session.expire_all()
            secure_order = m.db.session.get(m.DigitalOrder, secure_order.id)
            assert secure_order.payment_status == 'PENDING' and secure_order.main_order.status == 'SECURE_PAYMENT'
            m.requests.get = lambda *args, **kwargs: FakeResponse({'data': {'attributes': {'payment_intent': {'attributes': {'status': 'succeeded'}}}}})
            try:
                automatic_check = client.get(f'/api/digital/order/{secure_order.tracking_token}/payment-status')
            finally:
                m.requests.get = original_get
            automatic_data = automatic_check.get_json()
            assert automatic_check.status_code == 200 and automatic_data['paid'] and automatic_data['download_ready']
            m.db.session.expire_all()
            secure_order = m.db.session.get(m.DigitalOrder, secure_order.id)
            assert secure_order.payment_status == 'PAID' and secure_order.status == 'READY'
            assert secure_order.main_order.status == 'COMPLETED' and secure_order.main_order.payment_verified

            # The product's saved maximum device count is copied to the paid
            # order automatically. Each code binds to one device in an app.
            activation_codes = m.DigitalAppActivationCode.query.filter_by(order_id=secure_order.id).order_by(m.DigitalAppActivationCode.id).all()
            assert len(activation_codes) == 2 and all(code.status == 'UNUSED' for code in activation_codes)
            issued = client.post(f'/admin/digital/order/{secure_order.id}/activation-codes', data={'device_limit': '3'})
            assert issued.status_code == 302
            assert m.DigitalAppActivationCode.query.filter_by(order_id=secure_order.id).count() == 3
            activation = client.post('/api/digital/app/activate', json={
                'activation_code': activation_codes[0].activation_code,
                'device_id': 'smoke-device-0001', 'device_name': 'Smoke Test Phone',
            })
            activation_data = activation.get_json()
            assert activation.status_code == 200 and activation_data['success'] and activation_data['activation_token']
            reused = client.post('/api/digital/app/activate', json={
                'activation_code': activation_codes[0].activation_code,
                'device_id': 'smoke-device-0002', 'device_name': 'Another device',
            })
            assert reused.status_code == 403
            validation = client.post('/api/digital/app/validate', json={
                'activation_token': activation_data['activation_token'], 'device_id': 'smoke-device-0001',
            })
            assert validation.status_code == 200 and validation.get_json()['success']
            paid_page = client.get(f'/digital/order/{secure_order.tracking_token}')
            assert paid_page.status_code == 200 and b'Your app activation codes' in paid_page.data

            try:
                with m.app.test_request_context('/'):
                    from werkzeug.datastructures import FileStorage
                    m.digital_asset_from_upload(FileStorage(stream=io.BytesIO(b'no'), filename='unsafe.exe', content_type='application/octet-stream'))
                raise AssertionError('Executable digital asset was incorrectly accepted')
            except m.OrderValidationError:
                pass

            admin_page = client.get('/admin/digital')
            assert admin_page.status_code == 200
            assert b'protected digital asset' in admin_page.data.lower() and b'Draft with Gemini' in admin_page.data and b'upload update' in admin_page.data

    print('DIGITAL ASSETS, SECURE CHECKOUT + PAYPAL, AUTOMATIC RELEASE, AI FAQ, AND APP ACTIVATION SMOKE CHECK PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
