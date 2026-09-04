#!/usr/bin/env python3
"""Isolated behavioral smoke test for Macleen's Community release."""
from __future__ import annotations

import os
import sys
import tempfile
import io
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
        from PIL import Image, ImageStat
        import app as m

        m.app.config.update(TESTING=True)
        with m.app.app_context():
            product = m.Product(name="Smoke Test Snack", category_name="Street Food", price=20, cost=8, stock=2, is_active=True)
            m.db.session.add(product)
            people = []
            for index, (name, handle, role) in enumerate((
                ("Campus Tester", "campus.tester", "STUDENT"),
                ("Town Tester", "town.tester", "RESIDENT"),
                ("Community Owner", "uzu.macky", "RESIDENT"),
                ("Town Viewer", "town.viewer", "RESIDENT"),
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
                    is_community_admin=handle == "uzu.macky",
                    first_post_approved=handle != "campus.tester",
                )
                m.db.session.add(profile)
                m.db.session.flush()
                people.append((cust, profile))
            m.db.session.commit()

            client = m.app.test_client()
            share_version = m.product_share_version(product)
            crawler_headers = {
                "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
            }
            m._PRODUCT_SHARE_CACHE.clear()
            product_page = client.get(f"/product/{product.id}?pv={share_version}", headers=crawler_headers)
            assert f"{product.id}:{share_version}" in m._PRODUCT_SHARE_CACHE
            preview = client.get(f"/social/product/{product.id}/{share_version}.jpg", headers=crawler_headers)
            assert preview.status_code == 200
            assert preview.content_type == "image/jpeg"
            assert preview.data[:3] == b"\xff\xd8\xff" and len(preview.data) > 25_000
            decoded_preview = Image.open(io.BytesIO(preview.data)).convert("RGB")
            assert decoded_preview.size == (1200, 630)
            assert sum(ImageStat.Stat(decoded_preview).var) > 1000
            assert b"og:image:type\" content=\"image/jpeg" in product_page.data
            assert f"/social/product/{product.id}/{share_version}.jpg".encode() in product_page.data
            assert m._marketing_source_link("PRODUCT", product.id, "FOODHOUSE").endswith(f"/product/{product.id}?pv={share_version}")
            legacy_preview = client.get(f"/social/product/{product.id}.png", follow_redirects=False)
            assert legacy_preview.status_code == 302 and legacy_preview.headers["Location"].endswith(f"/{share_version}.jpg")

            with client.session_transaction() as browser_session:
                browser_session["customer_id"] = people[0][0].id

            page = client.get("/community")
            assert page.status_code == 200 and b'data-feed="CAMPUS"' in page.data
            assert b'data-feed="TOWN"' not in page.data and b"switchCommunityFeed('TOWN')" not in page.data

            first = client.post("/community/api/posts", data={
                "channel": "CAMPUS", "module": "CAMPUS_BOARD", "post_type": "TEXT",
                "body": "Smoke-test campus announcement for @uzu.macky",
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
            assert m.CommunityMention.query.filter_by(post_id=post.id, mentioned_profile_id=people[2][1].id).count() == 1
            assert m.CommunityNotification.query.filter_by(recipient_profile_id=people[2][1].id, kind="MENTION").count() == 1

            # Resident receives only Town Square. Main admin alone receives both feeds.
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[1][0].id
            town_page = client.get("/community")
            assert b'data-feed="TOWN"' in town_page.data and b'data-feed="CAMPUS"' not in town_page.data
            assert b"People you may know" in town_page.data and b"town.viewer" in town_page.data
            assert b"campus.tester" not in town_page.data
            public_profile = client.get("/community/member/town.viewer")
            assert public_profile.status_code == 200 and b"Town Viewer" not in public_profile.data
            follow = client.post("/community/api/follows/uzu.macky")
            assert follow.status_code == 200 and follow.json["following"] is True and follow.json["points_awarded"] == 0.5
            assert client.post("/community/api/follows/uzu.macky").json["following"] is False
            refollow = client.post("/community/api/follows/uzu.macky")
            assert refollow.json["following"] is True and refollow.json["points_awarded"] == 0.0

            admin_post = m.CommunityPost(
                author_profile_id=people[2][1].id, channel="TOWN", module="MUNICIPAL_BULLETIN",
                post_type="TEXT", body="Owner update", status="PUBLISHED", published_at=m.utc_now(),
            )
            m.db.session.add(admin_post)
            m.db.session.commit()
            liked = client.post(f"/community/api/posts/{admin_post.id}/react", json={"reaction_type": "LIKE"})
            assert liked.status_code == 200 and liked.json["points_awarded"] == 0.2
            assert client.post(f"/community/api/posts/{admin_post.id}/react", json={"reaction_type": "LIKE"}).json["active"] is False
            liked_again = client.post(f"/community/api/posts/{admin_post.id}/react", json={"reaction_type": "LIKE"})
            assert liked_again.json["active"] is True and liked_again.json["points_awarded"] == 0.0
            commented = client.post(f"/community/api/posts/{admin_post.id}/comments", json={"body": "Helpful update, thank you!"})
            assert commented.status_code == 200 and commented.json["comment"]["handle"] == "@town.tester"
            reshared = client.post(f"/community/api/posts/{admin_post.id}/reshare", json={"channel": "TOWN"})
            assert reshared.status_code == 200 and reshared.json["pending"] is False
            reshared_post = m.CommunityPost.query.filter_by(author_profile_id=people[1][1].id, reshared_post_id=admin_post.id).one()
            assert reshared_post.status == "PUBLISHED" and reshared.json["post"]["original"]["body"] == "Owner update"
            assert client.post(f"/community/api/posts/{admin_post.id}/reshare", json={"channel": "TOWN"}).status_code == 400

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[2][0].id
            owner_page = client.get("/community")
            assert b'data-feed="CAMPUS"' in owner_page.data and b'data-feed="TOWN"' in owner_page.data
            assert client.get("/community/member/campus.tester").status_code == 200

            # Member post API enforces words-only even if a modified client sends poll fields.
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[0][0].id
            assert client.get("/community/member/town.viewer").status_code == 404
            rejected_format = client.post("/community/api/posts", data={
                "channel": "CAMPUS", "module": "CAMPUS_BOARD", "post_type": "POLL",
                "body": "Modified client", "poll_option": ["A", "B"],
            })
            assert rejected_format.status_code == 400 and "word-only" in rejected_format.json["message"]

            # A self-applying student must submit an image; approval erases it.
            applicant = m.Customer(
                name="ID Applicant", contact="09987770001", pin_hash=generate_password_hash("1234"),
                card_number="MFH-9901", points_balance=0,
            )
            m.db.session.add(applicant)
            m.db.session.commit()
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = applicant.id
            student_form = {
                "handle": "id.applicant", "role": "STUDENT", "campus_name": "CHMSU Binalbagan Campus",
                "department": "Business", "graduating_year": str(m.ph_today().year + 1), "privacy_consent": "on",
            }
            missing_id = client.post("/community/profile", data=student_form, headers={"X-Macleens-Community": "1"})
            assert missing_id.status_code == 400 and "student ID" in missing_id.json["message"]
            id_buffer = io.BytesIO()
            Image.new("RGB", (600, 380), "white").save(id_buffer, format="PNG")
            id_buffer.seek(0)
            with_id = client.post(
                "/community/profile", data={**student_form, "student_id": (id_buffer, "student-id.png")},
                headers={"X-Macleens-Community": "1"}, content_type="multipart/form-data",
            )
            assert with_id.status_code == 200
            applicant_profile = m.CommunityProfile.query.filter_by(customer_id=applicant.id).one()
            assert applicant_profile.verification_status == "PENDING" and applicant_profile.student_id_image_data.startswith("data:image/webp;base64,")
            assert m.CommunityAdminNotice.query.filter_by(kind="NEW_MEMBER", profile_id=applicant_profile.id, is_read=False).count() == 1
            assert m.CommunityNotification.query.filter_by(recipient_profile_id=people[2][1].id, kind="MEMBER_JOIN", target_key=f"profile:{applicant_profile.id}").count() == 1
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["admin_user"] = "admin"
                browser_session["_staff_last_activity"] = datetime.now().isoformat()
            admin_page = client.get("/admin/community")
            assert admin_page.status_code == 200 and b"Community Admin join alerts" in admin_page.data and b"id.applicant" in admin_page.data
            assert client.post("/admin/community/notices/read").status_code == 302
            assert m.CommunityAdminNotice.query.filter_by(is_read=False).count() == 0
            assert client.post(f"/admin/community/profile/{applicant_profile.id}/verification", data={"action": "VERIFY"}).status_code == 302
            m.db.session.refresh(applicant_profile)
            assert applicant_profile.verification_status == "VERIFIED" and applicant_profile.student_id_image_data is None
            assert applicant_profile.student_id_deleted_at is not None

            # Admin may pre-approve a known loyalty customer; self-registration
            # then needs no ID image and a forged role edit still cannot switch roles.
            preapproved = m.Customer(
                name="Known Student", contact="09987770002", pin_hash=generate_password_hash("1234"),
                card_number="MFH-9902", points_balance=0,
            )
            m.db.session.add(preapproved)
            m.db.session.commit()
            tagged = client.post("/admin/community/student-tag", data={"customer_identifier": "MFH-9902"})
            assert tagged.status_code == 302
            m.db.session.refresh(preapproved)
            assert preapproved.community_student_preapproved is True
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = preapproved.id
            preapproved_join = client.post("/community/profile", data={
                "handle": "known.student", "role": "STUDENT", "campus_name": "Binalbagan Catholic College",
                "department": "Education", "graduating_year": str(m.ph_today().year + 1), "privacy_consent": "on",
            }, headers={"X-Macleens-Community": "1"})
            assert preapproved_join.status_code == 200
            assert m.CommunityProfile.query.filter_by(customer_id=preapproved.id).one().verification_status == "VERIFIED"

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[1][0].id
            forged_switch = client.post("/community/profile", data={
                "handle": "town.tester", "role": "STUDENT", "barangay": "San Pedro", "resident_since_year": "2020",
            }, headers={"X-Macleens-Community": "1"})
            assert forged_switch.status_code == 200
            m.db.session.refresh(people[1][1])
            assert people[1][1].role == "RESIDENT"

            # A lock hides profile details from ordinary same-role viewers, but
            # an accepted connection unlocks the profile without exposing loyalty data.
            locked = client.post("/community/profile", data={
                "handle": "town.tester", "role": "RESIDENT", "barangay": "San Pedro",
                "resident_since_year": "2020", "public_bio": "Private smoke-test bio",
                "is_profile_locked": "on",
            }, headers={"X-Macleens-Community": "1"})
            assert locked.status_code == 200 and locked.json["profile_locked"] is True
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[3][0].id
            locked_page = client.get("/community/member/town.tester")
            assert locked_page.status_code == 200 and b"This profile is locked" in locked_page.data
            assert b"Private smoke-test bio" not in locked_page.data
            connection_request = client.post("/community/api/connections", json={"action": "REQUEST", "handle": "town.tester"})
            assert connection_request.status_code == 200
            connection = m.CommunityConnection.query.one()
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[1][0].id
            assert client.post("/community/api/connections", json={"action": "ACCEPT", "connection_id": connection.id}).status_code == 200
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[3][0].id
            unlocked_page = client.get("/community/member/town.tester")
            assert unlocked_page.status_code == 200 and b"Private smoke-test bio" in unlocked_page.data

            # Invite-only, role-locked group chats support messages, assigned
            # tasks, shared notes, live polls, reporting, and leaving without
            # exposing ordinary chat content to the admin review page.
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[1][0].id
            invalid_group = client.post("/community/api/groups", json={
                "name": "Mixed Role Group", "invite_handles": "@campus.tester",
            })
            assert invalid_group.status_code == 400 and "role-locked" in invalid_group.json["message"]
            created_group = client.post("/community/api/groups", json={
                "name": "Town Project Team", "invite_handles": "@town.viewer",
            })
            assert created_group.status_code == 200
            group = m.CommunityGroup.query.one()
            invite = m.CommunityGroupMember.query.filter_by(
                group_id=group.id, profile_id=people[3][1].id,
            ).one()
            assert invite.status == "INVITED"
            assert m.CommunityNotification.query.filter_by(
                recipient_profile_id=people[3][1].id, kind="GROUP_INVITE",
            ).count() == 1
            owner_group_page = client.get(created_group.json["url"])
            assert owner_group_page.status_code == 200
            assert b"Private group" in owner_group_page.data and b'id="taskForm"' in owner_group_page.data

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[3][0].id
            assert client.get(created_group.json["url"], follow_redirects=False).status_code == 302
            assert client.get(f"/community/api/groups/{group.id}/messages").status_code == 403
            accepted = client.post(f"/community/api/group-invites/{invite.id}", json={"action": "ACCEPT"})
            assert accepted.status_code == 200 and accepted.json["url"] == created_group.json["url"]
            assert client.get(created_group.json["url"]).status_code == 200

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[1][0].id
            sent = client.post(f"/community/api/groups/{group.id}/messages", json={"body": "Town project kickoff"})
            assert sent.status_code == 200 and sent.json["pending"] is False
            group_message = m.CommunityGroupMessage.query.one()
            task_created = client.post(f"/community/api/groups/{group.id}/tasks", json={
                "action": "CREATE", "title": "Collect requirements", "details": "List the needed materials",
                "assigned_to_profile_id": people[3][1].id, "priority": "HIGH",
                "due_date": m.ph_today().isoformat(),
            })
            assert task_created.status_code == 200 and task_created.json["task"]["assignee"] == "@town.viewer"
            task = m.CommunityGroupTask.query.one()
            note_created = client.post(f"/community/api/groups/{group.id}/notes", json={
                "action": "CREATE", "title": "Decision log", "body": "Meet beside the Food House at 3 PM.",
            })
            assert note_created.status_code == 200
            note = m.CommunityGroupNote.query.one()
            assert client.post(f"/community/api/groups/{group.id}/notes", json={
                "action": "TOGGLE_PIN", "note_id": note.id,
            }).json["note"]["is_pinned"] is True
            poll_created = client.post(f"/community/api/groups/{group.id}/polls", json={
                "action": "CREATE", "question": "Preferred meetup time?",
                "options": "2 PM\n3 PM\n4 PM", "duration_hours": 24,
            })
            assert poll_created.status_code == 200 and len(poll_created.json["poll"]["options"]) == 3
            poll = m.CommunityGroupPoll.query.one()
            option = poll.options[1]

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[3][0].id
            received = client.get(f"/community/api/groups/{group.id}/messages?after_id=0")
            assert received.status_code == 200 and received.json["messages"][0]["body"] == "Town project kickoff"
            task_done = client.post(f"/community/api/groups/{group.id}/tasks", json={
                "action": "STATUS", "task_id": task.id, "status": "DONE",
            })
            assert task_done.status_code == 200 and task_done.json["task"]["status"] == "DONE"
            voted = client.post(f"/community/api/groups/{group.id}/polls", json={
                "action": "VOTE", "poll_id": poll.id, "option_id": option.id,
            })
            assert voted.status_code == 200 and voted.json["poll"]["total_votes"] == 1
            report = client.post(f"/community/api/group-messages/{group_message.id}/report", json={
                "reason": "OTHER", "details": "Private smoke-test report",
            })
            assert report.status_code == 200 and report.json["quarantined"] is False

            # An unrelated Campus member cannot enter a Town group even by URL/API.
            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[0][0].id
            assert client.get(f"/community/api/groups/{group.id}/messages").status_code == 403

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["admin_user"] = "admin"
                browser_session["_staff_last_activity"] = datetime.now().isoformat()
            group_admin_page = client.get("/admin/community")
            assert group_admin_page.status_code == 200 and b"Private group-message safety review" in group_admin_page.data
            assert b"Town project kickoff" in group_admin_page.data
            assert client.post(
                f"/admin/community/group-message/{group_message.id}/status", data={"action": "PUBLISH"},
            ).status_code == 302
            m.db.session.refresh(group_message)
            assert group_message.status == "PUBLISHED" and group_message.flags_count == 0

            with client.session_transaction() as browser_session:
                browser_session.clear()
                browser_session["customer_id"] = people[3][0].id
            left = client.post(f"/community/api/groups/{group.id}/members", json={"action": "LEAVE"})
            assert left.status_code == 200
            m.db.session.refresh(invite)
            assert invite.status == "LEFT"
            assert client.get(f"/community/api/groups/{group.id}/messages").status_code == 403

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
