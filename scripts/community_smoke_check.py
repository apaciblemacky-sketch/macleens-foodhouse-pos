#!/usr/bin/env python3
"""Isolated behavioral smoke test for Community Lite v6."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mfh-community-lite-") as folder:
        db_path = (Path(folder) / "community.db").resolve().as_posix()
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["SECRET_KEY"] = "isolated-community-lite-check"
        os.environ["COMMUNITY_INTERNAL_CHAT_OPEN"] = "false"
        os.environ["COMMUNITY_SOCIAL_REWARDS_OPEN"] = "false"
        os.environ["COMMUNITY_GIFTING_OPEN"] = "false"
        os.environ["COMMUNITY_RESHARING_OPEN"] = "false"

        from werkzeug.security import generate_password_hash
        import app as m

        m.app.config.update(TESTING=True)
        with m.app.app_context():
            people = {}
            rows = (
                ("Campus Tester", "campus.tester", "STUDENT"),
                ("Town Tester", "town.tester", "RESIDENT"),
                ("Community Owner", "uzu.macky", "RESIDENT"),
                ("Town Viewer", "town.viewer", "RESIDENT"),
            )
            for index, (name, handle, role) in enumerate(rows, 1):
                customer = m.Customer(
                    name=name, contact=f"0998111000{index}", pin_hash=generate_password_hash("1234"),
                    card_number=f"MFH-97{index:02d}", points_balance=60, accumulated_spend=95,
                )
                m.db.session.add(customer)
                m.db.session.flush()
                profile = m.CommunityProfile(
                    customer_id=customer.id, handle=handle, role=role,
                    campus_name="CHMSU Binalbagan Campus" if role == "STUDENT" else None,
                    department="Business" if role == "STUDENT" else None,
                    graduating_year=m.ph_today().year + 2 if role == "STUDENT" else None,
                    barangay="San Pedro" if role == "RESIDENT" else None,
                    resident_since_year=2020 if role == "RESIDENT" else None,
                    verification_status="VERIFIED" if role == "STUDENT" else "SELF_DECLARED",
                    is_community_admin=handle == "uzu.macky", first_post_approved=handle == "uzu.macky",
                )
                m.db.session.add(profile)
                m.db.session.flush()
                people[handle] = (customer, profile)
            product = m.Product(name="Smoke Snack", category_name="Street Food", price=20, cost=8, stock=2, is_active=True)
            ad = m.CommunityAd(title="Smoke Ad", body="Useful offer", target_role="ALL", channel="ALL", cta_url="/", is_active=True)
            m.db.session.add_all([product, ad])
            m.db.session.commit()

            client = m.app.test_client()

            def login(handle: str) -> None:
                with client.session_transaction() as browser:
                    browser.clear()
                    browser["customer_id"] = people[handle][0].id

            def admin_login() -> None:
                with client.session_transaction() as browser:
                    browser.clear()
                    browser["admin_user"] = "admin"
                    browser["_staff_last_activity"] = datetime.now().isoformat()

            login("campus.tester")
            campus_page = client.get("/community")
            assert campus_page.status_code == 200
            assert b'data-feed="CAMPUS"' in campus_page.data and b'data-feed="TOWN"' not in campus_page.data
            assert b'data-community-tab="gifts"' not in campus_page.data
            assert b'data-community-tab="rankings"' not in campus_page.data
            assert b"No points for likes or follows" in campus_page.data

            # The first three safe posts need review; the fourth publishes immediately.
            for number in range(1, 4):
                login("campus.tester")
                response = client.post("/community/api/posts", data={
                    "channel": "CAMPUS", "module": "CAMPUS_BOARD", "post_type": "TEXT",
                    "body": f"Reviewed campus update {number} for @uzu.macky",
                })
                assert response.status_code == 200 and response.json["pending"] is True
                post = m.CommunityPost.query.order_by(m.CommunityPost.id.desc()).first()
                admin_login()
                assert client.post(f"/admin/community/post/{post.id}/status", data={"action": "PUBLISH"}).status_code == 302
            login("campus.tester")
            fourth = client.post("/community/api/posts", data={
                "channel": "CAMPUS", "module": "CAMPUS_BOARD", "post_type": "TEXT",
                "body": "Trusted campus update four",
            })
            assert fourth.status_code == 200 and fourth.json["pending"] is False
            wrong_feed = client.post("/community/api/posts", data={
                "channel": "TOWN", "module": "LOCAL_CLASSIFIEDS", "post_type": "TEXT", "body": "Wrong feed",
            })
            assert wrong_feed.status_code == 400

            # Follows, likes, and comments stay AJAX but never award loyalty points.
            login("town.tester")
            starting_points = people["town.tester"][0].points_balance
            followed = client.post("/community/api/follows/uzu.macky")
            assert followed.status_code == 200 and followed.json["points_awarded"] == 0
            owner_post = m.CommunityPost(
                author_profile_id=people["uzu.macky"][1].id, channel="TOWN",
                module="MUNICIPAL_BULLETIN", post_type="TEXT", body="Owner safety update",
                status="PUBLISHED", published_at=m.utc_now(),
            )
            m.db.session.add(owner_post)
            m.db.session.commit()
            liked = client.post(f"/community/api/posts/{owner_post.id}/react", json={"reaction_type": "LIKE"})
            commented = client.post(f"/community/api/posts/{owner_post.id}/comments", json={"body": "Helpful update"})
            assert liked.status_code == 200 and liked.json["points_awarded"] == 0
            assert commented.status_code == 200 and commented.json["comment"]["handle"] == "@town.tester"
            m.db.session.refresh(people["town.tester"][0])
            assert people["town.tester"][0].points_balance == starting_points
            assert client.post(f"/community/api/posts/{owner_post.id}/reshare", json={}).status_code == 410
            assert client.post("/community/api/gifts", json={}).status_code == 410

            # Student applicants use an in-person visual check; no ID blob is stored.
            applicant = m.Customer(
                name="Student Applicant", contact="09987771111", pin_hash=generate_password_hash("1234"),
                card_number="MFH-9799", points_balance=0,
            )
            m.db.session.add(applicant)
            m.db.session.commit()
            with client.session_transaction() as browser:
                browser.clear()
                browser["customer_id"] = applicant.id
            joined = client.post("/community/profile", data={
                "handle": "student.applicant", "role": "STUDENT",
                "campus_name": "CHMSU Binalbagan Campus", "department": "Business",
                "graduating_year": str(m.ph_today().year + 1), "privacy_consent": "on",
            }, headers={"X-Macleens-Community": "1"})
            assert joined.status_code == 200
            applicant_profile = m.CommunityProfile.query.filter_by(customer_id=applicant.id).one()
            assert applicant_profile.verification_status == "PENDING"
            assert applicant_profile.verification_method == "IN_PERSON_PENDING"
            assert applicant_profile.student_id_image_data is None
            assert m.CommunityAdminNotice.query.filter_by(kind="NEW_MEMBER", profile_id=applicant_profile.id).count() == 0
            assert client.post("/community/api/student-id-resubmit").status_code == 410

            # Two workspaces per member; tasks/notes/polls stay, live chat is off.
            login("town.tester")
            invalid_group = client.post("/community/api/groups", json={"name": "Mixed Role Group", "invite_handles": "@campus.tester"})
            assert invalid_group.status_code == 400
            first_group = client.post("/community/api/groups", json={
                "name": "Town Project Team", "invite_handles": "@town.viewer",
                "external_chat_url": "https://m.me/example",
            })
            assert first_group.status_code == 200
            group = m.db.session.get(m.CommunityGroup, first_group.json["group_id"])
            assert group.external_chat_url == "https://m.me/example"
            assert client.post(f"/community/api/groups/{group.id}/messages", json={"body": "No live polling"}).status_code == 410
            assert client.post("/community/api/groups", json={"name": "Town Tasks Two"}).status_code == 200
            third_group = client.post("/community/api/groups", json={"name": "Town Tasks Three"})
            assert third_group.status_code == 400 and "up to 2" in third_group.json["message"]
            task = client.post(f"/community/api/groups/{group.id}/tasks", json={
                "action": "CREATE", "title": "Collect requirements", "details": "List materials",
                "assigned_to_profile_id": people["town.tester"][1].id, "priority": "HIGH",
            })
            note = client.post(f"/community/api/groups/{group.id}/notes", json={
                "action": "CREATE", "title": "Decision log", "body": "Meet at 3 PM.",
            })
            poll = client.post(f"/community/api/groups/{group.id}/polls", json={
                "action": "CREATE", "question": "Preferred time?", "options": "2 PM\n3 PM", "duration_hours": 24,
            })
            assert task.status_code == note.status_code == poll.status_code == 200
            group_page = client.get(first_group.json["url"])
            assert b"Purpose-based Community Lite workspace" in group_page.data
            assert b"setInterval(pollMessages,5000)" not in group_page.data

            # Ad views do not create writes; deliberate clicks remain measurable.
            before = ad.impression_count
            impression = client.post(f"/community/api/ads/{ad.id}/impression")
            m.db.session.refresh(ad)
            assert impression.status_code == 200 and impression.json["recorded"] is False
            assert ad.impression_count == before

            admin_login()
            admin_page = client.get("/admin/community")
            assert admin_page.status_code == 200
            assert b"Community Lite safety controls" in admin_page.data
            assert b"Student checks pending" in admin_page.data
            assert b"Priority verification and safety alerts" in admin_page.data

            # Migration erases any legacy ID blob without deleting the profile.
            applicant_profile.student_id_image_data = "data:image/webp;base64,legacy"
            m.db.session.commit()
            m.run_schema_migrations()
            m.db.session.expire_all()
            applicant_profile = m.db.session.get(m.CommunityProfile, applicant_profile.id)
            assert applicant_profile.student_id_image_data is None
            assert applicant_profile.student_id_deleted_at is not None

            health = client.get("/healthz")
            assert health.status_code == 200 and health.json["community_mode"] == "lite"

    print("COMMUNITY LITE SMOKE CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
