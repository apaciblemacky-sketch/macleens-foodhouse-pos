#!/usr/bin/env python3
"""Verify the tablet kiosk is inaccessible and the Cashier tablet layout renders."""
from __future__ import annotations

import os
import sys
import tempfile
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
            client = m.app.test_client()
            with client.session_transaction() as browser:
                browser['cashier_user'] = 'cashier-layout-smoke'
                browser['_staff_last_activity'] = '2026-09-08T00:00:00'
            page = client.get('/pos/cashier')
            assert page.status_code == 200
            for marker in [b'cashierQueuePanel', b'cashierStatusPanel', b'Counter Tray', b'Pending']:
                assert marker in page.data
            assert client.get('/tablet').status_code == 404
            assert client.post('/api/tablet-checkout', json={}).status_code == 404

    print('CASHIER TABLET LAYOUT + TABLET REMOVAL SMOKE CHECK PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
