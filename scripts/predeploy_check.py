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
        "minimum_order_amount", "option_schema", "stock", "is_active", "available_start_time", "available_end_time",
    },
    "order": {
        "id", "order_type", "dining_option", "customer_id", "subtotal",
        "total_amount", "payment_method", "payment_verified", "status",
        "is_unpaid", "created_at",
    },
    "order_item": {
        "id", "order_id", "product_id", "unit_price", "cost_price",
        "quantity", "subtotal", "selected_options",
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

    option_markers = [
        "option_schema = db.Column",
        "selected_options = db.Column",
        "validate_product_options",
        "selected_options=line.get('selected_options_json')",
    ]
    missing_options = [marker for marker in option_markers if marker not in source]
    if missing_options:
        fail("product sub-option safeguards are missing: " + ", ".join(missing_options))
    required_option_ui = ["Choices / Sub-options", "collectProductOptions", "options: posCart[id].options || {}"]
    missing_option_ui = [marker for marker in required_option_ui if marker not in admin_template + cashier_template]
    if missing_option_ui:
        fail("product sub-option UI is incomplete: " + ", ".join(missing_option_ui))
    ok("product sauce/flavor sub-options are configurable and server-validated")

    adjustment_markers = [
        "@app.route('/pos/adjust-order/<int:order_id>'",
        "[Cashier Add-on]",
        "Only cashier-added charge lines can be removed here.",
        "cash received/change-for is only",
    ]
    missing_adjustments = [marker for marker in adjustment_markers if marker not in source]
    if missing_adjustments:
        fail("pending-order cashier adjustment safeguards are missing: " + ", ".join(missing_adjustments))
    if "openOrderAdjustModal" not in cashier_template or "＋₱ ADJUST" not in cashier_template:
        fail("cashier pending-order adjustment UI is missing")
    ok("cashier can add/remove controlled extra fees before accepting pending orders")

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

    cashflow_markers = [
        "class CashFlowPlan(db.Model):",
        "CASH_FLOW_COGS_RATE = 0.60",
        "@app.route('/admin/cash-flow')",
        "@app.route('/admin/cashflow')",
        "@app.route('/admin/cash-flow/plan/save', methods=['POST'])",
        "cashflow_occurrence_dates",
        "total_rev = order_rev + vault_drop_sales",
    ]
    missing_cashflow = [marker for marker in cashflow_markers if marker not in source]
    if missing_cashflow:
        fail("cash-flow portal safeguards are missing: " + ", ".join(missing_cashflow))
    if "cash_flow_portal" not in admin_template or "Cash Flow Manager" not in admin_template:
        fail("admin header is missing the Cash Flow Manager portal button")
    ok("admin header links to the cash-flow portal")

    cashflow_template = TEMPLATES / "cash_flow_portal.html"
    if not cashflow_template.exists():
        fail("templates/cash_flow_portal.html is missing")
    cashflow_html = cashflow_template.read_text(encoding="utf-8")
    for marker in ["horizon_months", "COGS @ 60%", "Additional Income", "Duration / Occurrences", "Planning Duration (Years)"]:
        if marker not in cashflow_html:
            fail(f"cash-flow portal UI is missing: {marker}")
    if "BIWEEKLY" not in source or "Bi-weekly (Every 2 Weeks)" not in cashflow_html:
        fail("cash-flow portal is missing Bi-weekly (every 2 weeks) recurrence")
    ok("cash-flow Bi-weekly recurrence is present")

    horizon_markers = [
        "CASH_FLOW_MAX_HORIZON_YEARS = 20",
        "horizon_years =",
        "horizon_months = horizon_years * 12",
        "for month_index in range(horizon_months)",
        "duration_count=0 means indefinite",
    ]
    missing_horizon = [marker for marker in horizon_markers if marker not in source]
    if missing_horizon:
        fail("cash-flow extended horizon/indefinite recurrence is missing: " + ", ".join(missing_horizon))
    for marker in ["Indefinite / No End Date", "INDEFINITE", "No end date", "max_horizon_years"]:
        if marker not in cashflow_html:
            fail(f"cash-flow extended horizon/indefinite UI is missing: {marker}")
    ok("cash-flow supports 1-20 year horizons and indefinite recurring income/expenses")

    projection_markers = [
        "average_daily_sales =",
        "actual_sales_days",
        "cashflow_sales_for_day",
        "projection_daily_sales",
        "@app.route('/admin/cash-flow/projection/save', methods=['POST'])",
        "cashflow_projection_mode",
        "cashflow_average_window",
        "cashflow_manual_daily_sales",
        "cashflow_manual_start_date",
        "manual_start_date",
    ]
    missing_projection = [marker for marker in projection_markers if marker not in source]
    if missing_projection:
        fail("cash-flow average-sales projection is missing: " + ", ".join(missing_projection))
    for marker in ["Blank-Day Sales Projection", "Use Specific Daily Sales Amount", "Specific Amount Starting Date", "3-Day Average", "7-Day Average", "15-Day Average", "30-Day Average", "Lifetime Average", "Use Average Again", "Actual / Projected"]:
        if marker not in cashflow_html:
            fail(f"cash-flow projection controls UI is missing: {marker}")
    if "day >= manual_start_date" not in source or "average is used before the start date" not in cashflow_html:
        fail("cash-flow manual projection start-date behavior is missing")
    ok("cash-flow projection supports a manual start date plus 3/7/15/30/lifetime actual-sales averages")

    # Guard against accidentally copying monthly-only fields into the daily table.
    daily_marker = "{% for row in daily_rows %}"
    if daily_marker not in cashflow_html:
        fail("cash-flow daily detail loop is missing")
    daily_section = cashflow_html.split(daily_marker, 1)[1].split("{% endfor %}", 1)[0]
    invalid_daily_fields = [
        "row.actual_sales",
        "row.actual_days",
        "row.projected_sales",
        "row.projected_days",
    ]
    leaked_fields = [field for field in invalid_daily_fields if field in daily_section]
    if leaked_fields:
        fail("cash-flow daily table references monthly-only fields: " + ", ".join(leaked_fields))
    if daily_section.count("<td") != 9:
        fail(f"cash-flow daily table should render 9 cells per row, found {daily_section.count('<td')}")
    ok("cash-flow daily detail uses only valid daily-row fields")

    ok("flexible-horizon cash-flow portal and automatic 60% COGS rule are present")

    craft_markers = [
        "class CraftItem(db.Model):",
        "class CraftSiteVisitor(db.Model):",
        "class CraftItemView(db.Model):",
        "class CraftItemLike(db.Model):",
        "class CraftOrder(db.Model):",
        "class CraftLedger(db.Model):",
        "@app.route('/craft')",
        "@app.route('/admin/craft')",
        "create_main_craft_order",
        "sync_craft_order_after_main_verification",
        "order_type='CRAFT'",
        "category='Craft Shop'",
    ]
    missing_craft = [marker for marker in craft_markers if marker not in source]
    if missing_craft:
        fail("integrated Craft Shop markers are missing: " + ", ".join(missing_craft))
    for rel in ["craft/base.html", "craft/index.html", "craft/item_detail.html", "craft/order_form.html", "craft/order_success.html", "craft/admin.html"]:
        if not (TEMPLATES / rel).exists():
            fail(f"integrated Craft Shop template is missing: {rel}")
    if "craft_revenue_total" not in admin_template or "Craft Shop" not in admin_template:
        fail("master admin does not show separate Craft Shop revenue")
    if "craft_store" not in storefront:
        fail("Food House storefront does not link to the integrated Craft Shop")
    if "sync_craft_order_after_main_verification(order, accepted=True)" not in source or "sync_craft_order_after_main_verification(order, accepted=False)" not in source:
        fail("cashier verification is not synchronized back to Craft Shop orders")
    if "ensure_legacy_craft_catalog()" not in source or "LEGACY_CRAFT_CATALOG" not in source:
        fail("former standalone Craft Shop catalog is not seeded into the unified Craft Shop")
    craft_base = (TEMPLATES / "craft/base.html").read_text(encoding="utf-8")
    if "Craft Admin" in craft_base or "url_for('staff_login')" in craft_base:
        fail("public Craft Shop still exposes an admin/staff navigation button")
    craft_detail = (TEMPLATES / "craft/item_detail.html").read_text(encoding="utf-8")
    craft_index = (TEMPLATES / "craft/index.html").read_text(encoding="utf-8")
    per_ip_markers = [
        "uq_craft_item_view_ip", "uq_craft_item_like_ip",
        "CraftItemLike.query.filter_by(item_id=item.id, ip_address=ip)",
        "CraftComment(item_id=item.id, author=author, content=content, ip_address=ip)",
    ]
    missing_ip = [marker for marker in per_ip_markers if marker not in source]
    if missing_ip:
        fail("Craft per-IP engagement safeguards are missing: " + ", ".join(missing_ip))
    if "One like per product per IP" not in craft_detail or "unique-IP views" not in craft_detail:
        fail("Craft detail page does not explain/enforce unique-IP view/like behavior")
    if "shareLink" not in craft_base or "Share Craft Shop" not in craft_index:
        fail("Craft sharing controls are missing")
    craft_card = (TEMPLATES / "craft/_product_card.html").read_text(encoding="utf-8")
    if 'class="btn btn-outline craft-share-btn"' not in craft_card or 'data-share-title="{{ item.name|e }}"' not in craft_card:
        fail("Craft product-card Share button is not using the safe delegated data-attribute handler")
    if 'craft-share-btn' not in craft_detail or 'data-share-url=' not in craft_detail:
        fail("Craft product-detail Share button is not using the safe delegated data-attribute handler")
    if "event.target.closest('.craft-share-btn')" not in craft_base:
        fail("Craft delegated Share click handler is missing")
    if 'onclick="shareLink({{ item.name|tojson' in craft_card or 'onclick="shareLink({{ item.name|tojson' in craft_detail:
        fail("Craft product Share still contains fragile inline JSON onclick quoting")
    ok("Craft per-product Share buttons use the safe delegated click handler")
    if "shareStoreLink" not in storefront or "shareProductLink" not in storefront:
        fail("Food House storefront/product sharing controls are missing")
    product_detail_html = (TEMPLATES / "product_detail.html").read_text(encoding="utf-8")
    if "shareFoodProduct" not in product_detail_html:
        fail("Food House product detail sharing control is missing")
    share_helper = (ROOT / "static" / "share-helper.js").read_text(encoding="utf-8")
    if 'data-share="whatsapp"' in share_helper or 'data-share="telegram"' in share_helper:
        fail("Share dialog still exposes WhatsApp or Telegram buttons")
    if "wa.me/" in share_helper or "t.me/share" in share_helper:
        fail("Share helper still contains WhatsApp or Telegram share handlers")
    if "mfhFacebookShare" not in share_helper or "window.location.href = url" in share_helper:
        fail("Facebook sharing may still replace the Food House/Craft page instead of using a popup")
    if "mail.google.com/mail/?view=cm&fs=1" not in share_helper or "mfhEmailShare" not in share_helper:
        fail("Email sharing is not wired to the working Gmail compose popup")
    for rel in ["store_catalog.html", "product_detail.html", "craft/base.html"]:
        content = (TEMPLATES / rel).read_text(encoding="utf-8")
        if "share-helper.js') }}?v=4" not in content:
            fail(f"{rel} does not load the latest share helper cache version")
    ok("Share menu uses Facebook popup + Gmail email, without WhatsApp/Telegram")
    header_section = admin_template[:5000]
    if "url_for('craft_admin_dashboard')" in header_section:
        fail("master admin header still exposes a Craft Shop admin shortcut; Craft Admin should be direct-link only")
    ok("Craft Shop keeps legacy UI, per-IP views/likes/comments tracking, sharing, cashier sync, and direct-link-only admin access")

    print("\nPRE-DEPLOY CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
