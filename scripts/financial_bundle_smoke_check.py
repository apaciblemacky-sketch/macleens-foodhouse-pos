#!/usr/bin/env python3
"""Isolated behavioral smoke check for Financial Statements v8 and bundle deals."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='mfh-financial-v8-') as folder:
        db_path = (Path(folder) / 'financial.db').resolve().as_posix()
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        os.environ['SECRET_KEY'] = 'financial-bundle-smoke-check'

        from werkzeug.security import generate_password_hash
        import app as m

        m.app.config.update(TESTING=True)
        with m.app.app_context():
            m.db.create_all()
            m.run_schema_migrations()
            today = m.ph_today()
            customer = m.Customer(name='Financial Tester', contact='09981234567', pin_hash=generate_password_hash('1234'))
            first = m.Product(name='Bundle Rice', category_name='Meals', price=30, cost=12, stock=12, is_active=True)
            second = m.Product(name='Bundle Drink', category_name='Drinks', price=20, cost=7, stock=12, is_active=True)
            m.db.session.add_all([customer, first, second])
            m.db.session.flush()

            bundle = m.BundleDeal(name='Lunch Bundle', discount_type='FIXED', discount_value=5, is_active=True)
            m.db.session.add(bundle)
            m.db.session.flush()
            m.db.session.add_all([
                m.BundleDealItem(bundle_id=bundle.id, product_id=first.id, quantity=1),
                m.BundleDealItem(bundle_id=bundle.id, product_id=second.id, quantity=1),
            ])
            order = m.Order(order_type='PICKUP', customer_id=customer.id, customer_name=customer.name,
                            contact_number=customer.contact, subtotal=50, total_amount=50,
                            payment_method='CASH', status='COMPLETED', created_at=m.utc_now())
            m.db.session.add(order)
            m.db.session.flush()
            m.db.session.add_all([
                m.OrderItem(order_id=order.id, product_id=first.id, product_name=first.name, unit_price=30, cost_price=12, quantity=1, subtotal=30),
                m.OrderItem(order_id=order.id, product_id=second.id, product_name=second.name, unit_price=20, cost_price=7, quantity=1, subtotal=20),
                m.Expense(title='Packaging supplies', amount=4, category='Supplies', created_at=m.utc_now()),
            ])
            plan = m.CashFlowPlan(entry_type='EXPENSE', title='Personal cash-flow test', amount=6, frequency='DAILY', start_date=today, duration_count=1, category='General', is_active=True)
            m.db.session.add(plan)
            m.db.session.commit()

            pricing = m.bundle_deal_pricing(bundle)
            assert pricing['regular_price'] == 50 and pricing['bundle_price'] == 45 and pricing['discount_amount'] == 5
            lines = m.validate_and_lock_cart([{'bundle_id': bundle.id, 'quantity': 1}], require_available=True)
            assert len(lines) == 2 and round(m.cart_subtotal(lines), 2) == 45.00
            assert sum(line['quantity'] for line in lines) == 2

            exclusion_map = m.financial_exclusion_map()
            journal, controls = m.financial_build_journal(today, today, 60, include_scheduled=True, exclusions=exclusion_map)
            assert any(row['source_kind'] == 'ORDER' for row in journal)
            assert any(row['source_kind'] == 'EXPENSE' for row in journal)
            assert any(row['source_kind'] == 'CASHFLOW_PLAN' for row in journal)
            by_ref = {}
            for row in journal:
                by_ref.setdefault(row['entry_ref'], [0.0, 0.0])
                by_ref[row['entry_ref']][0] += row['debit']
                by_ref[row['entry_ref']][1] += row['credit']
            assert all(abs(debit - credit) < 0.011 for debit, credit in by_ref.values())
            pnl = m.financial_income_statement(journal)
            assert round(pnl['sales'], 2) == 50.00
            assert round(pnl['cogs'], 2) == 19.00
            assert any(row['source_kind'] == 'CASHFLOW_PLAN' for row in controls)

            m.db.session.add_all([
                m.FinancialJournalEntry(entry_date=today, entry_ref='ADJ-SMOKE', description='Opening capital', account='Cash & Digital Collections', debit=100, credit=0, created_by='admin'),
                m.FinancialJournalEntry(entry_date=today, entry_ref='ADJ-SMOKE', description='Opening capital', account='Owner Capital', debit=0, credit=100, created_by='admin'),
            ])
            m.db.session.commit()
            journal, _ = m.financial_build_journal(today, today, 60, include_scheduled=True)
            assert any(row['entry_ref'] == 'ADJ-SMOKE' and not row['is_auto'] for row in journal)
            assert m.financial_cash_flows(journal)['financing'] == 100

            client = m.app.test_client()
            with client.session_transaction() as browser:
                browser['admin_user'] = 'admin'
                browser['_staff_last_activity'] = datetime.now().isoformat()
            response = client.get('/admin/financial-statements')
            assert response.status_code == 200
            assert b'Financial Statements' in response.data and b'Daily adjusting entry' in response.data
            admin_page = client.get('/admin')
            assert admin_page.status_code == 200 and b'Product Bundle Deals' in admin_page.data
            storefront = client.get('/')
            assert storefront.status_code == 200 and b'Lunch Bundle' in storefront.data

    print('FINANCIAL STATEMENTS + BUNDLE DEALS V8 SMOKE CHECK PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
