#!/usr/bin/env python3
"""Verify the tablet kiosk is inaccessible and the Cashier tablet layout renders."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    source = (ROOT / 'app.py').read_text(encoding='utf-8')
    cashier_template = (ROOT / 'templates' / 'cashier_pos.html').read_text(encoding='utf-8')
    assert "@app.route('/tablet')" not in source
    assert "@app.route('/api/tablet-checkout'" not in source
    for marker in [
        'cashierQueuePanel', 'cashierStatusPanel', 'cashier-side-tabs',
        'isAndroidOrTabletCashier', 'tablet-pos-mode', 'Counter Tray',
        'selectCashierSideTab', "data-cashier-side-section=\"unpaid\"",
        'cashierLocalClock', 'updateCashierLocalClock', 'printingModal',
        'Record Misc Sale', 'Record Printing Sale', "service_type\" value=\"PRINTING",
        "claimed_at|ph_datetime",
    ]:
        assert marker in cashier_template, f'Missing Cashier responsive marker: {marker}'

    with tempfile.TemporaryDirectory(prefix='mfh-cashier-layout-v20-') as folder:
        db_path = (Path(folder) / 'cashier-layout.db').resolve().as_posix()
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        os.environ['SECRET_KEY'] = 'cashier-tablet-layout-smoke-check'
        import app as m

        m.app.config.update(TESTING=True)
        with m.app.app_context():
            m.db.create_all()
            m.run_schema_migrations()
            assert m.ph_datetime_filter(datetime(2026, 9, 8, 5, 56), '%b %d, %I:%M %p') == 'Sep 08, 01:56 PM'
            client = m.app.test_client()
            with client.session_transaction() as browser:
                browser['cashier_user'] = 'cashier-layout-smoke'
                browser['_staff_last_activity'] = datetime.now().isoformat()
            page = client.get('/pos/cashier')
            assert page.status_code == 200
            for marker in [b'cashierQueuePanel', b'cashierStatusPanel', b'Counter Tray', b'Pending', b'cashierLocalClock', b'Record Printing Sale']:
                assert marker in page.data

            misc_sale = client.post('/pos/misc-sale', data={
                'service_type': 'MISC', 'service_name': 'Special Packaging', 'amount': '12.50',
                'payment_method': 'CASH', 'notes': 'smoke test',
            })
            printing_sale = client.post('/pos/misc-sale', data={
                'service_type': 'PRINTING', 'service_name': 'Document Printing', 'amount': '20.00',
                'payment_method': 'GCASH', 'notes': 'two pages',
            })
            assert misc_sale.status_code == 302 and printing_sale.status_code == 302
            misc_item = m.OrderItem.query.filter(m.OrderItem.product_name.like('[Misc]%')).one()
            printing_item = m.OrderItem.query.filter(m.OrderItem.product_name.like('[Printing]%')).one()
            assert misc_item.product_name == '[Misc] Special Packaging'
            assert printing_item.product_name == '[Printing] Document Printing'
            assert client.get('/tablet').status_code == 404
            assert client.post('/api/tablet-checkout', json={}).status_code == 404

    print('CASHIER TABLET LAYOUT, LOCAL TIME, SEPARATE PRINTING, + TABLET REMOVAL SMOKE CHECK PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
