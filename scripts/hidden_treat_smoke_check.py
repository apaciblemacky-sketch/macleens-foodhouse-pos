#!/usr/bin/env python3
"""Isolated checks for Hidden Treat rewards and cashier flexible-price lines."""
from __future__ import annotations

import os
import sys
import tempfile
from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def live_hunt(m, *, title, location, prize_type, now, **values):
    return m.HiddenPrizeHunt(
        title=title,
        location=location,
        prize_type=prize_type,
        starts_at=now - timedelta(minutes=2),
        ends_at=now + timedelta(days=1),
        **values,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='mfh-hidden-treat-v18-') as folder:
        db_path = (Path(folder) / 'hidden-treat.db').resolve().as_posix()
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        os.environ['SECRET_KEY'] = 'hidden-treat-smoke-check'

        import app as m

        m.app.config.update(TESTING=True)
        with m.app.app_context():
            m.db.create_all()
            m.run_schema_migrations()
            now = m.utc_now()
            member = m.Customer(
                name='Hidden Treat Tester', contact='09981230123',
                pin_hash=generate_password_hash('1234'), accumulated_spend=700,
            )
            flexible = m.Product(
                name='Flexible Rice Meal', category_name='Ulam', price=20, cost=7,
                allow_custom_amount=True, minimum_order_amount=20, stock=20, is_active=True,
            )
            free_product = m.Product(
                name='Hidden Treat Drink', category_name='Drinks', price=30, cost=9,
                stock=5, is_active=True,
            )
            m.db.session.add_all([member, flexible, free_product])
            m.db.session.flush()

            points_hunt = live_hunt(
                m, title='Portal Points Test', location='LOYALTY_PORTAL', prize_type='POINTS',
                now=now, placement_slot='LOYALTY_REWARDS', display_size_px=52,
                points_amount=3, max_winners=1,
            )
            voucher_hunt = live_hunt(
                m, title='Store Voucher Test', location='STOREFRONT_PRODUCT', prize_type='VOUCHER',
                now=now, placement_slot='STOREFRONT_IMAGE_TOP_RIGHT', display_size_px=64,
                location_product_id=flexible.id, voucher_discount_percent=10,
                voucher_min_order=20, max_winners=1,
            )
            product_hunt = live_hunt(
                m, title='Community Product Test', location='COMMUNITY', prize_type='PRODUCT',
                now=now, prize_product_id=free_product.id, max_winners=1,
            )
            community_placement_hunt = live_hunt(
                m, title='Community Placement Test', location='COMMUNITY', prize_type='POINTS',
                now=now, placement_slot='COMMUNITY_PEOPLE', display_size_px=58,
                points_amount=2, max_winners=1,
            )
            profile = m.CommunityProfile(
                customer_id=member.id, handle='hidden-tester', role='RESIDENT',
                barangay=m.BINALBAGAN_BARANGAYS[0], resident_since_year=2020,
                verification_status='VERIFIED', verification_method='SELF_DECLARED',
                first_post_approved=True,
            )
            m.db.session.add_all([points_hunt, voucher_hunt, product_hunt, community_placement_hunt, profile])
            m.db.session.commit()
            assert m.hidden_prize_placement_slot(points_hunt) == 'LOYALTY_REWARDS'
            assert m.hidden_prize_display_size(voucher_hunt) == 64
            assert m.hidden_prize_hunts_by_slot([voucher_hunt])['STOREFRONT_IMAGE_TOP_RIGHT'][0].id == voucher_hunt.id

            # Two different entered amounts for one flexible-price product stay
            # as two order lines, even in the same cashier order.
            separate_lines = m.validate_and_lock_cart([
                {'product_id': flexible.id, 'quantity': 1, 'options': {}, 'unit_price': 20},
                {'product_id': flexible.id, 'quantity': 1, 'options': {}, 'unit_price': 27},
            ], require_available=False, allow_cashier_custom_amount=True)
            assert len(separate_lines) == 2
            assert sorted(line['unit_price'] for line in separate_lines) == [20.0, 27.0]
            assert round(m.cart_subtotal(separate_lines), 2) == 47.0

            member_client = m.app.test_client()
            with member_client.session_transaction() as browser:
                browser['customer_id'] = member.id

            # A points treat awards once and cannot be farmed by repeatedly
            # opening or pressing the visible gift.
            first_points = member_client.post(f'/api/hidden-prizes/{points_hunt.id}/claim')
            assert first_points.status_code == 200 and first_points.get_json()['prize_type'] == 'POINTS'
            m.db.session.refresh(member)
            assert round(member.points_balance, 2) == 3.0
            repeat_points = member_client.post(f'/api/hidden-prizes/{points_hunt.id}/claim')
            assert repeat_points.status_code == 200 and repeat_points.get_json()['already_claimed']
            assert m.HiddenPrizeClaim.query.filter_by(hunt_id=points_hunt.id, customer_id=member.id).count() == 1

            # The account-bound voucher is claimed from its storefront product
            # placement, then the cashier may use it for that same member only.
            voucher_response = member_client.post(f'/api/hidden-prizes/{voucher_hunt.id}/claim')
            voucher_body = voucher_response.get_json()
            assert voucher_response.status_code == 200 and voucher_body['prize_type'] == 'VOUCHER'
            voucher_code = voucher_body['claim_code']

            cashier_client = m.app.test_client()
            with cashier_client.session_transaction() as browser:
                browser['cashier_user'] = 'cashier-smoke'
                browser['_staff_last_activity'] = datetime.now().isoformat()
            sale = cashier_client.post('/pos/direct-sale', json={
                'items': [{'product_id': flexible.id, 'quantity': 1, 'options': {}, 'unit_price': 27}],
                'dining_option': 'TAKEOUT', 'customer_type': 'REGISTERED',
                'registered_customer_id': member.id, 'payment_method': 'CASH',
                'change_for': 100, 'redeem_points': 0, 'hidden_prize_code': voucher_code,
                'notes': 'Hidden Treat smoke test',
            })
            sale_body = sale.get_json()
            assert sale.status_code == 200 and sale_body['success']
            assert round(sale_body['hidden_prize_discount'], 2) == 2.70
            order = m.db.session.get(m.Order, sale_body['order_id'])
            assert round(order.hidden_prize_discount, 2) == 2.70
            assert m.HiddenPrizeClaim.query.filter_by(claim_code=voucher_code).first().status == 'REDEEMED'

            # Product prizes reserve stock at claim time and do not deduct it
            # again when cashier records the free handover.
            free_claim_response = member_client.post(f'/api/hidden-prizes/{product_hunt.id}/claim')
            free_claim_body = free_claim_response.get_json()
            assert free_claim_response.status_code == 200 and free_claim_body['prize_type'] == 'PRODUCT'
            m.db.session.refresh(free_product)
            assert free_product.stock == 4
            free_claim = m.HiddenPrizeClaim.query.filter_by(claim_code=free_claim_body['claim_code']).first()
            redeemed = cashier_client.post(f'/pos/redeem-hidden-prize/{free_claim.id}')
            assert redeemed.status_code == 302
            m.db.session.refresh(free_product)
            m.db.session.refresh(free_claim)
            assert free_product.stock == 4 and free_claim.status == 'REDEEMED'

            # Expired product claims return their reserved stock even when the
            # next request is only a read-only dashboard page.
            # The real schema requires a customer. Create a second member solely
            # to prove expiry safely returns a previously reserved unit.
            expiry_member = m.Customer(
                name='Expired Claim Tester', contact='09981230999',
                pin_hash=generate_password_hash('1234'),
            )
            m.db.session.add(expiry_member)
            m.db.session.flush()
            expired_claim = m.HiddenPrizeClaim(
                hunt_id=product_hunt.id, customer_id=expiry_member.id,
                claim_code='HUNT-EXPIRED1', status='AVAILABLE', stock_reserved=True,
                expires_at=now - timedelta(minutes=1),
            )
            free_product.stock -= 1
            m.db.session.add(expired_claim)
            m.db.session.commit()
            m.expire_hidden_prize_claims(persist=True)
            m.db.session.refresh(free_product)
            m.db.session.refresh(expired_claim)
            assert free_product.stock == 4 and expired_claim.status == 'EXPIRED' and not expired_claim.stock_reserved

            with cashier_client.session_transaction() as browser:
                browser['admin_user'] = 'admin'
            ph_end = m.utc_naive_to_ph(now + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
            image_buffer = BytesIO()
            Image.new('RGB', (640, 480), '#d946ef').save(image_buffer, format='PNG')
            admin_created = cashier_client.post('/admin/hidden-prizes/create', data={
                'title': 'Admin Form Test', 'location': 'LOYALTY_PORTAL', 'prize_type': 'POINTS',
                'placement_slot': 'LOYALTY_FAVORITES', 'display_size_px': '76',
                'display_image': (BytesIO(image_buffer.getvalue()), 'treat.png'),
                'points_amount': '1', 'max_winners': '1', 'ends_at': ph_end, 'is_active': 'on',
            })
            assert admin_created.status_code == 302
            admin_hunt = m.HiddenPrizeHunt.query.filter_by(title='Admin Form Test').one()
            assert admin_hunt.placement_slot == 'LOYALTY_FAVORITES'
            assert admin_hunt.display_size_px == 76
            assert (admin_hunt.display_image_data or '').startswith('data:image/webp;base64,')
            display_update = cashier_client.post(
                f'/admin/hidden-prizes/{admin_hunt.id}/display', data={
                    'placement_slot': 'LOYALTY_ACCOUNT', 'display_size_px': '110',
                    'remove_display_image': 'on',
                },
            )
            assert display_update.status_code == 302
            m.db.session.refresh(admin_hunt)
            assert admin_hunt.placement_slot == 'LOYALTY_ACCOUNT'
            assert admin_hunt.display_size_px == 110 and admin_hunt.display_image_data is None
            admin_page = cashier_client.get('/admin')
            assert admin_page.status_code == 200 and b'Exact Display Area' in admin_page.data
            portal_page = member_client.get('/portal/dashboard')
            assert portal_page.status_code == 200 and b'hidden-treat-button' in portal_page.data
            storefront = member_client.get('/')
            assert storefront.status_code == 200 and b'hidden-treat-icon' in storefront.data
            community_page = member_client.get('/community')
            assert community_page.status_code == 200
            assert f'data-community-hunt="{community_placement_hunt.id}"'.encode() in community_page.data

    print('HIDDEN TREAT PLACEMENT + FLEXIBLE-PRICE CASHIER V23 SMOKE CHECK PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
