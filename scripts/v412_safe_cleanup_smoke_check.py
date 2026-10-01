"""
Macleen's Food House POS v41.2 Safe Cleanup Smoke Check
--------------------------------------------------------
Static/request-context verification only. It does NOT open the database,
delete data, or run migrations.

Run inside the project's Python 3.11 virtual environment:
    python scripts\v412_safe_cleanup_smoke_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# When this file is executed as ``python scripts\...``, Python puts the
# scripts directory first on sys.path.  This project also contains a legacy
# scripts/app.py, so explicitly import the real project-root app.py.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("PASS:", message)


def check_retired_path(path: str) -> None:
    with app.app.test_request_context(path):
        try:
            app.block_retired_features_v412()
        except Exception as exc:
            # Flask's abort(404) raises werkzeug.exceptions.NotFound.
            if getattr(exc, "code", None) != 404:
                raise
            print("PASS: retired path blocked ->", path)
            return
    raise AssertionError(f"Retired path was not blocked: {path}")


def main() -> int:
    check(
        str(app.APP_RELEASE).startswith("2026.09.25-safe-cleanup-v41.2"),
        f"release is {app.APP_RELEASE}",
    )

    for path in (
        "/community",
        "/community/member/test",
        "/investor",
        "/investors/interest",
        "/admin/investors",
        "/pos/investor-proposals",
        "/api/hidden-prizes/1/claim",
        "/admin/hidden-prizes/create",
        "/pos/redeem-hidden-prize/1",
        "/digital/apps/chat-lite/test-token",
        "/admin/chat-lite",
        "/admin/marketing",
        "/admin/marketing/generate",
        "/tasks/marketing/run",
        "/tasks/facebook-menu/run",
    ):
        check_retired_path(path)

    check(
        "craft_like_item" in app.RETIRED_META_ENDPOINTS
        and "craft_add_comment" in app.RETIRED_META_ENDPOINTS,
        "Craft like/comment endpoints are retired",
    )
    check(
        "/craft/item/" not in app.RETIRED_PATH_PREFIXES,
        "Craft product detail pages remain available",
    )
    check(
        app.ensure_chat_lite_digital_product() is None,
        "CHAT Lite startup hook is now a no-op",
    )
    print("\nSafe cleanup smoke check completed. No database was opened or modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
