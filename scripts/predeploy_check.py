#!/usr/bin/env python3
"""Macleen's Food House pre-deploy source and bundled SQLite checks.

Run from the project root:
    python scripts/predeploy_check.py

This intentionally uses only the Python standard library so it can catch basic
packaging/source problems even before Flask dependencies are installed.
"""
from __future__ import annotations

import ast
import json
import py_compile
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DB = ROOT / "instance" / "foodhouse_pos.db"

REQUIRED_DB_COLUMNS = {
    "customer": {
        "id", "contact", "pin_hash", "points_balance", "accumulated_spend",
        "card_number", "card_status", "card_expires_at", "is_credit_eligible",
        "credit_limit", "outstanding_ar", "referred_by", "last_daily_login",
        "login_streak", "last_active_at",
    },
    "product": {
        "id", "name", "category_name", "price", "cost", "allow_custom_amount",
        "minimum_order_amount", "stock", "is_active", "available_start_time", "available_end_time",
    },
    "order": {
        "id", "order_type", "dining_option", "customer_id", "subtotal",
        "total_amount", "payment_method", "payment_verified", "status",
        "is_unpaid", "created_at",
    },
    "order_item": {
        "id", "order_id", "product_id", "unit_price", "cost_price",
        "quantity", "subtotal",
    },
    "promotion_tracker": {"id", "promo_code", "promo_price", "promo_cost", "is_visible", "portal_only", "description"},
    "vault_drop": {"id", "drop_number", "amount", "cash_breakdown", "created_at"},
    "product_suggestion": {"id", "customer_id", "customer_name", "suggestion_text", "status", "created_at"},
    "bonus_campaign": {"id", "title", "bonus_points", "points_multiplier", "min_spend", "is_active"},
    "bonus_campaign_claim": {"id", "campaign_id", "customer_id", "order_id", "points_awarded"},
    "referral_reward": {"id", "referrer_customer_id", "referred_customer_id", "first_order_id"},
    "portal_event": {"id", "source", "event_type", "customer_id", "created_at"},
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f" OK : {message}")


def rendered_templates(source: str) -> set[str]:
    tree = ast.parse(source)
    result: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "render_template":
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            result.add(node.args[0].value)
    return result


def main() -> int:
    if not APP.exists():
        fail("app.py is missing")

    try:
        py_compile.compile(str(APP), doraise=True)
    except py_compile.PyCompileError as exc:
        fail(f"app.py does not compile: {exc.msg}")
    ok("app.py compiles")

    source = APP.read_text(encoding="utf-8")
    if "[cite:" in source:
        fail("citation artifacts are present in app.py")
    for template in TEMPLATES.rglob("*.html"):
        if "[cite:" in template.read_text(encoding="utf-8", errors="replace"):
            fail(f"citation artifacts are present in {template.relative_to(ROOT)}")
    ok("no accidental [cite: ...] artifacts")

    missing_templates = sorted(
        name for name in rendered_templates(source) if not (TEMPLATES / name).exists()
    )
    if missing_templates:
        fail("missing render_template targets: " + ", ".join(missing_templates))
    ok("all render_template targets exist")

    manifest = STATIC / "manifest.json"
    service_worker = STATIC / "sw.js"
    if not manifest.exists() or not service_worker.exists():
        fail("static/manifest.json or static/sw.js is missing")
    try:
        json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"manifest.json is invalid JSON: {exc}")
    ok("PWA manifest and service worker files exist")

    # The static fallback icon is optional because the store logo may come from StoreSetting,
    # but warn clearly if PWA icon fallbacks still point to a missing file.
    if not (STATIC / "logo.png").exists():
        print("WARN: static/logo.png is missing; add the real Food House logo for PWA/fallback icons.")

    if DB.exists():
        conn = sqlite3.connect(DB)
        try:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table, required in REQUIRED_DB_COLUMNS.items():
                if table not in tables:
                    fail(f"bundled SQLite DB is missing table {table!r}")
                columns = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}
                missing = sorted(required - columns)
                if missing:
                    fail(f"bundled SQLite DB {table!r} is missing columns: {', '.join(missing)}")
            ok("bundled SQLite schema contains all critical current columns")
        finally:
            conn.close()
    else:
        print("INFO: no bundled SQLite DB found; production DATABASE_URL will be checked at app startup.")

    # Detect the old failure mode where cashier query errors were converted into an empty queue.
    dangerous = re.search(
        r"pending_orders\s*=\s*Order\.query[\s\S]{0,600}?except\s+Exception\s*:\s*\n\s*pending_orders\s*=\s*\[\]",
        source,
    )
    if dangerous:
        fail("cashier pending-order DB errors are still being hidden as an empty queue")
    ok("cashier pending queue does not silently hide DB query failures")

    # Confirm the user's chosen accounting policy was not accidentally changed.
    if "total_rev = order_rev + vault_drop_sales" not in source:
        fail("vault drops are no longer included in the configured gross-sales calculation")
    ok("vault drops remain included in gross sales by project policy")

    engagement_markers = [
        "@app.route('/portal/suggest-product'",
        "@app.route('/admin/product-suggestion/<int:suggestion_id>/status'",
        "@app.route('/marketing/qr/<string:source>.svg'",
        "class ProductSuggestion(db.Model):",
        "class BonusCampaign(db.Model):",
        "class ReferralReward(db.Model):",
    ]
    missing = [marker for marker in engagement_markers if marker not in source]
    if missing:
        fail("current engagement update markers missing: " + ", ".join(missing))

    retired_routes = [
        "@app.route('/portal/claim-wifi'",
        "@app.route('/portal/wishlist/<int:product_id>'",
        "@app.route('/portal/vote/<int:product_id>'",
        "@app.route('/pos/topup-member-wifi'",
        "@app.route('/pos/update-wifi-minutes/",
    ]
    still_present = [marker for marker in retired_routes if marker in source]
    if still_present:
        fail("retired Wi-Fi/vote/wishlist routes are still present: " + ", ".join(still_present))
    ok("product suggestions are active and retired Wi-Fi/vote/wishlist routes are removed")

    storefront = (TEMPLATES / "store_catalog.html").read_text(encoding="utf-8")
    if "Top 10 VIP Reward Members" in storefront or "top_customers" in storefront:
        fail("public VIP rewards leaderboard is still present on the storefront")
    ok("public VIP rewards leaderboard is removed")

    admin_template = (TEMPLATES / "admin.html").read_text(encoding="utf-8")
    if "window.location.href='/admin?sort='" in admin_template:
        fail("admin product sorting still reloads the page")
    if "sortCatalogTable()" not in admin_template:
        fail("client-side admin product sorting is missing")
    ok("admin catalog sorting is client-side and preserves page/filter state")

    flexible_amount_markers = [
        "allow_custom_amount = db.Column",
        "minimum_order_amount = db.Column",
        "allow_cashier_custom_amount=True",
        "cannot be sold below its",
    ]
    missing_flexible = [marker for marker in flexible_amount_markers if marker not in source]
    if missing_flexible:
        fail("cashier specific-amount safeguards are missing: " + ", ".join(missing_flexible))
    cashier_template = (TEMPLATES / "cashier_pos.html").read_text(encoding="utf-8")
    if "Specific Product Amount" not in cashier_template or "minimumAmount" not in cashier_template:
        fail("cashier specific-amount UI is missing")
    ok("cashier specific amounts are product-controlled and minimum-enforced")

    # Guard against the portal/dashboard crash caused by passing an undefined local
    # variable (products=products) to Jinja after the old vote/wishlist UI was removed.
    dashboard_match = re.search(
        r"def customer_dashboard\(\):([\s\S]*?)(?=\n@app\.route|\nif __name__)",
        source,
    )
    if not dashboard_match:
        fail("customer_dashboard route could not be located")
    dashboard_source = dashboard_match.group(1)
    if re.search(r"\bproducts\s*=\s*products\b", dashboard_source):
        fail("customer_dashboard still passes an undefined products variable")
    ok("customer dashboard does not reference the retired undefined products context")

    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    if "qrcode" not in req.lower():
        fail("requirements.txt is missing qrcode dependency used by the QR kit")
    ok("QR dependency is declared")

    print("\nPRE-DEPLOY CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
