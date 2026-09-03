#!/usr/bin/env python3
"""Isolated behavioral smoke test for Macleen's Community release."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mfh-community-check-") as folder:
        db_path = (Path(folder) / "community.db").resolve().as_posix()
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ.setdefault("SECRET_KEY", "isolated-community-smoke-check")

        from werkzeug.security import generate_password_hash
        import app as m

        m.app.config.update(TESTING=True)
        with m.app.app_context():
            product = m.Product(name="Smoke Test Snack", category_name="Street Food", price=20, cost=8, stock=2, is_active=True)
            m.db.session.add(product)
            people = []
            for index, (name, handle, role) in enumerate((
                ("Campus Tester", "campus.tester", "STUDENT"),
                ("Town Tester", "town.tester", "RESIDENT"),
            ), 1):
                cust = m.Customer(
                    name=name, contact=f"0998000000{index}", pin_hash=generate_password_hash("1234"),
                    card_number=f"MFH-98{index:02d}", points_balance=60, accumulated_spend=95,
                )
                m.db.session.add(cust)
                m.db.session.flush()
                profile = m.CommunityProfile(
                    customer_id=cust.id, handle=handle, role=role,
                    campus_name="CHMSU Binalbagan Campus" if role == "STUDENT" else None,
                    department="Business" if role == "STUDENT" else None,
                    graduating_year=m.ph_today().year + 2 if role == "STUDENT" else None,
                    vibe_status="Quiet study mode" if role == "STUDENT" else None,
                    barangay="San Pedro" if role == "RESIDENT" else None,
                    resident_since_year=2020 if role == "RESIDENT" else None,
                    verification_status="VERIFIED" if role == "STUDENT" else "SELF_DECLARED",
                )
                m.db.session.add(profile)
                m.db.session.flush()
                people.append((cust, profile))
            m.db.session.commit()

            client = m.app.test_client()
            with client.session_transaction() as browser_session:
                browser_session["customer_id"] = people[0][0].id

            page = client.get("/community")
            assert page.status_code == 200 and b"Campus Hub" in page.data and b"Town Square" in page.data

            first = client.post("/community/api/posts", data={
                "channel": "CAMPUS", "module": "CAMPUS_BOARD", "post_type": "TEXT",
                "body": "Smoke-test campus announcement",
            })
            assert first.status_code == 200 and first.json["pending"] is True
            post = m.CommunityPost.query.one()
            wrong_feed = client.post("/community/api/posts", data={
                "channel": "TOWN", "module": "LOCAL_CLASSIFIEDS", "post_type": "TEXT", "body": "Wrong feed",
            })
            assert wrong_feed.status_code == 400

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["admin_user"] = "admin"
                browser_session["_staff_last_activity"] = datetime.now().isoformat()
            assert client.post(f"/admin/community/post/{post.id}/status", data={"action": "PUBLISH"}).status_code == 302
            m.db.session.refresh(post)
            assert post.status == "PUBLISHED"

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[0][0].id
            gift = client.post("/community/api/gifts", data={
                "recipient_handle": "town.tester", "gift_type": "PRODUCT",
                "product_id": product.id, "pin": "1234", "note": "Smoke test",
            })
            assert gift.status_code == 200
            voucher = m.CommunityGift.query.filter_by(gift_type="PRODUCT").one()
            m.db.session.refresh(product)
            assert voucher.status == "AVAILABLE" and product.stock == 1

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["cashier_user"] = "cashier1"
                browser_session["_staff_last_activity"] = datetime.now().isoformat()
            assert client.post(f"/pos/community-gift/{voucher.id}/redeem").status_code == 302
            m.db.session.refresh(voucher)
            m.db.session.refresh(product)
            assert voucher.status == "CLAIMED" and product.stock == 1
            assert client.get("/pos/cashier").status_code == 200

    print("COMMUNITY SMOKE CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
