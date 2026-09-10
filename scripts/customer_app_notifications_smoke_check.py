#!/usr/bin/env python3
"""Lightweight source guard for installed-app notification controls.

This intentionally avoids importing Flask or opening the production database.
Run from the project root with ``python scripts/customer_app_notifications_smoke_check.py``.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: Path, *markers: str) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise SystemExit(f"FAIL: {path.relative_to(ROOT)} is missing: {', '.join(missing)}")


def main() -> int:
    require(
        ROOT / "app.py",
        "class CustomerAppAnnouncement(db.Model):",
        "community_admin_create_app_announcement",
        "'CATALOG': 'New items and store adjustments'",
        "'sound': category in app_notification_sound_categories()",
    )
    require(ROOT / "static" / "sw.js", "addEventListener('push'", "showNotification", "silent: payload.sound === false")
    for relative in ["templates/admin.html", "templates/digital/admin.html", "templates/craft/admin.html"]:
        require(ROOT / relative, "Send installed-app update", "community_admin_create_app_announcement")
    require(ROOT / "templates/customer_dashboard.html", "appNotificationPreference", "Enable app notifications")
    print("OK: installed-app update broadcasts, sound request, and opt-in controls are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
