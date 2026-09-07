#!/usr/bin/env python3
"""Focused checks for storefront QR Ph, COD, delivery details, and live chat."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = status_code < 300
        self.content = b'{}'

    def json(self):
        return self._payload


def checkout_payload(product_id, **extra):
    payload = {
        'items': [{'product_id': product_id, 'quantity': 1, 'options': {}}],
        'order_type': 'PICKUP', 'target_time': 'ASAP (20 mins)',
        'payment_method': 'CASH', 'change_for': 100, 'notes': '',
    }
    payload.update(extra)
    return payload


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='mfh-storefront-qrph-v17-') as folder:
        db_path = (Path(folder) / 'storefront.db').resolve().as_posix()
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        os.environ['SECRET_KEY'] = 'storefront-qrph-chat-smoke-check'
        os.environ['PAYMONGO_SECRET_KEY'] = 'sk_test_storefront_smoke_only'
        import app as m

        m.app.config.update(TESTING=True)
        with m.app.app_context():
            m.db.create_all()
            m.run_schema_migrations()
            customer = m.Customer(
                name='Checkout Tester', contact='09981230000', email='tester@example.com',
                pin_hash=generate_password_hash('1234'), is_cod_eligible=False,
            )
            product = m.Product(name='Smoke Palabok', category_name='Ulam', price=55, cost=20, stock=12, is_active=True)
            detail_zone = m.DeliveryZone(place_name='Detailed Zone', barangay='San Pedro', rate=30, distance='1 km', requires_detailed_address=True)
            zone_only = m.DeliveryZone(place_name='Zone Handoff', barangay='Paglaum', rate=30, distance='2 km', requires_detailed_address=False)
            m.db.session.add_all([customer, product, detail_zone, zone_only])
            m.save_digital_setting('storefront_gcash_gateway_mode', 'PAYMONGO')
            m.db.session.commit()
            m.check_operating_status = lambda: {
                'store_open': True, 'delivery_open': True,
                'settings': SimpleNamespace(store_open_time='08:00', store_close_time='19:00', delivery_open_time='09:00', delivery_close_time='17:00'),
            }

            customer_client = m.app.test_client()
            with customer_client.session_transaction() as browser:
                browser['customer_id'] = customer.id
            storefront = customer_client.get('/')
            assert storefront.status_code == 200 and b'GCash QR Ph' in storefront.data and b'Need help?' in storefront.data

            # Cash bill is mandatory, delivery COD requires the staff switch,
            # and detailed zones do not accept an address without a landmark.
            missing_bill = customer_client.post('/api/storefront-checkout', json=checkout_payload(product.id, change_for=None))
            assert missing_bill.status_code == 400 and b'cash bill' in missing_bill.data.lower()
            denied_cod = customer_client.post('/api/storefront-checkout', json=checkout_payload(
                product.id, order_type='DELIVERY', delivery_zone_id=detail_zone.id,
                delivery_address='Purok 3', landmark='Blue gate', payment_method='CASH', change_for=100,
            ))
            assert denied_cod.status_code == 403 and b'cash on delivery' in denied_cod.data.lower()
            missing_landmark = customer_client.post('/api/storefront-checkout', json=checkout_payload(
                product.id, order_type='DELIVERY', delivery_zone_id=detail_zone.id,
                delivery_address='Purok 3', landmark='', payment_method='GCASH',
            ))
            assert missing_landmark.status_code == 400 and b'landmark' in missing_landmark.data.lower()

            # QR Ph uses a hosted HTTPS link and does not trust the client to
            # claim payment. The thank-you message is created with the order.
            original_post, original_get = m.requests.post, m.requests.get
            captured = {}
            try:
                def fake_post(url, **kwargs):
                    captured.update(kwargs.get('json') or {})
                    captured['url'] = url
                    return FakeResponse({'data': {'id': 'cs_storefront_smoke', 'attributes': {'checkout_url': 'https://checkout.paymongo.test/storefront'}}})

                m.requests.post = fake_post
                response = customer_client.post('/api/storefront-checkout', json=checkout_payload(
                    product.id, order_type='DELIVERY', delivery_zone_id=zone_only.id,
                    delivery_address='', landmark='', payment_method='GCASH', change_for=None,
                ))
                body = response.get_json()
                assert response.status_code == 200 and body['success'] and body['payment_redirect_url'] == 'https://checkout.paymongo.test/storefront'
                assert captured['url'].endswith('/v2/checkout_sessions')
                assert captured['data']['attributes']['payment_method_types'] == ['qrph']
                order = m.db.session.get(m.Order, body['order_id'])
                assert order.payment_gateway == 'PAYMONGO' and order.delivery_address.startswith('Barangay: Paglaum')
                assert m.CustomerChatMessage.query.filter_by(order_id=order.id, sender_type='SYSTEM').count() == 1

                m.requests.get = lambda *args, **kwargs: FakeResponse({'data': {'attributes': {'payment_intent': {'attributes': {'status': 'succeeded'}}}}})
                assert m.storefront_check_paymongo_payment(order) and order.payment_verified
            finally:
                m.requests.post, m.requests.get = original_post, original_get

            # Both accounts exchange messages by polling APIs; no page reload
            # or public contact information is needed.
            tracker = customer_client.get(f'/order/track/{order.public_token}')
            assert tracker.status_code == 200 and b'Live cashier chat' in tracker.data
            first_messages = customer_client.get('/api/customer-chat/messages', query_string={'order_token': order.public_token})
            assert first_messages.status_code == 200 and first_messages.get_json()['messages']
            customer_message = customer_client.post('/api/customer-chat/messages', query_string={'order_token': order.public_token}, json={'message': 'Please let me know when it is ready.'})
            assert customer_message.status_code == 200 and customer_message.get_json()['success']

            cashier = m.app.test_client()
            with cashier.session_transaction() as browser:
                browser['cashier_user'] = 'cashier-smoke'
                browser['_staff_last_activity'] = datetime.now().isoformat()
            threads = cashier.get('/api/cashier/customer-chats')
            thread_data = threads.get_json()
            thread_key = f'order-{order.id}'
            assert threads.status_code == 200 and any(row['thread_key'] == thread_key for row in thread_data['threads'])
            staff_reply = cashier.post(f'/api/cashier/customer-chats/{thread_key}', json={'message': 'We will message you once it is ready.'})
            assert staff_reply.status_code == 200 and staff_reply.get_json()['success']
            received = customer_client.get('/api/customer-chat/messages', query_string={'order_token': order.public_token}).get_json()
            assert any(row['sender_type'] == 'CASHIER' for row in received['messages'])

            # Completing an order erases its temporary conversation.
            order.status = 'COMPLETED'
            order.fulfillment_status = 'READY'
            m.db.session.commit()
            fulfilled = cashier.post(f'/pos/order/{order.id}/fulfillment', data={'fulfillment_status': 'FULFILLED'})
            assert fulfilled.status_code == 302
            assert m.CustomerChatMessage.query.filter_by(order_id=order.id).count() == 0

    print('STOREFRONT QR PH, COD, DELIVERY DETAIL, AND TEMPORARY LIVE CHAT SMOKE CHECK PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
