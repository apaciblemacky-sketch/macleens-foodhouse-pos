#!/usr/bin/env python3
"""Behavioral checks for the v12 loyalty, delivery, card, and order-history upgrade."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='mfh-loyalty-v12-') as folder:
        db_path = (Path(folder) / 'loyalty.db').resolve().as_posix()
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        os.environ['SECRET_KEY'] = 'loyalty-v12-smoke-check'
        import app as m

        m.app.config.update(TESTING=True)
        with m.app.app_context():
            m.db.create_all()
            m.run_schema_migrations()
            source = m.Customer(name='Legacy Member', contact='09981110000', pin_hash=generate_password_hash('1234'), points_balance=3, accumulated_spend=90)
            target = m.Customer(name='New Member', contact='09982220000', pin_hash=generate_password_hash('1234'), points_balance=0, accumulated_spend=0)
            m.db.session.add_all([source, target])
            m.db.session.flush()
            old_order = m.Order(
                order_type='PICKUP', dining_option='PICKUP', customer_id=source.id, customer_name=source.name,
                contact_number=source.contact, subtotal=90, total_amount=90, payment_method='CASH',
                payment_verified=True, status='COMPLETED', fulfillment_status='FULFILLED',
            )
            m.db.session.add(old_order)
            m.db.session.add_all([
                m.DeliveryZone(place_name='Old ₱40 Zone', barangay='Test', rate=40, distance='1 km'),
                m.DeliveryZone(place_name='Old ₱80 Zone', barangay='Test', rate=80, distance='2 km'),
                m.DeliveryZone(place_name='Unchanged Zone', barangay='Test', rate=25, distance='3 km'),
            ])
            m.db.session.commit()

            # Historical orders are snapshotted at the old earning rate.  New
            # sales use the new ₱40 rule without changing past balances.
            # app.py runs setup at import, so reset only these one-time marker
            # rows to reproduce a pre-v12 database before invoking the upgrade.
            m.StoreSetting.query.filter(m.StoreSetting.key.in_([
                'loyalty_base_points_snapshot_v12', 'delivery_fee_rebase_v12',
            ])).delete(synchronize_session=False)
            m.db.session.commit()
            m.ensure_loyalty_and_delivery_upgrade_defaults()
            m.db.session.commit()
            m.db.session.refresh(old_order)
            assert m.loyalty_points_per_purchase() == 40
            assert old_order.base_points_earned == 3
            assert m.loyalty_points_from_amount(119) == 2
            rates = {zone.place_name: zone.rate for zone in m.DeliveryZone.query.all()}
            assert rates == {'Old ₱40 Zone': 30.0, 'Old ₱80 Zone': 65.0, 'Unchanged Zone': 25.0}

            # Reinstating an existing verified order moves its stored loyalty
            # value, never recalculates it using the future rate.
            m.reassign_order_to_customer(old_order, target)
            m.db.session.commit()
            assert old_order.customer_id == target.id
            assert source.points_balance == 0 and source.accumulated_spend == 0
            assert target.points_balance == 3 and target.accumulated_spend == 90

            m._DB_INITIALIZED = True
            client = m.app.test_client()
            with client.session_transaction() as browser:
                browser['admin_user'] = 'admin'
                browser['_staff_last_activity'] = datetime.now().isoformat()
            history = client.get(f'/admin/customer/{target.id}/purchase-history')
            assert history.status_code == 200
            assert b'Purchase History' in history.data and b'Reinstate an old order' in history.data and b'#1' in history.data
            cards = client.get(f'/admin/loyalty-cards?customer_id={target.id}')
            assert cards.status_code == 200
            assert b'2 \xc3\x97 2 inch' in cards.data
            assert b'SCAN TO OPEN YOUR REWARDS' in cards.data
            assert b'Terms' not in cards.data and b'PIN private' not in cards.data
            assert m.loyalty_card_qr_data_url('https://example.test/portal/login').startswith('data:image/png;base64,')
            admin = client.get('/admin')
            assert admin.status_code == 200 and b'spend per 1 point' in admin.data

    print('LOYALTY ₱40, DELIVERY 30/65, 2X2 CARD, AND PURCHASE HISTORY V12 SMOKE CHECK PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
