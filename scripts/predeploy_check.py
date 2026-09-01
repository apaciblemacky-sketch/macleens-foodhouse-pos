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
        "login_streak", "last_active_at", "card_theme", "card_logo_scale",
        "card_photo_scale", "card_qr_scale", "card_text_scale", "card_info_scale",
    },
    "product": {
        "id", "name", "category_name", "price", "cost", "allow_custom_amount",
        "minimum_order_amount", "option_schema", "size_schema", "stock", "is_active", "available_start_time", "available_end_time",
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
    "menu_vote_candidate": {"id", "name", "normalized_name", "category_name", "product_id", "is_active", "created_at"},
    "menu_preference_vote": {"id", "customer_id", "candidate_id", "period_key", "created_at"},
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
        "class MenuVoteCandidate(db.Model):",
        "class MenuPreferenceVote(db.Model):",
        "@app.route('/portal/menu-vote/<int:candidate_id>'",
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
    ok("product suggestions are active; legacy menu-vote data is preserved while the active voting workflow is retired")

    storefront = (TEMPLATES / "store_catalog.html").read_text(encoding="utf-8")
    if "Top 10 VIP Reward Members" in storefront or "top_customers" in storefront:
        fail("public VIP rewards leaderboard is still present on the storefront")
    ok("public VIP rewards leaderboard is removed")

    if 'href="/staff/login"' in storefront or '>Staff</a>' in storefront:
        fail("public Food House storefront still exposes a Staff login button")
    ok("public Food House storefront no longer exposes the Staff button")

    # Public storefront visibility: Active controls visibility. Optional availability
    # times control ordering only, so Featured/Best Seller products do not disappear
    # from the storefront outside their selling window.
    route_match = re.search(r"def store_catalog\(\):([\s\S]*?)(?=\n@app\.route)", source)
    if not route_match:
        fail("store_catalog route could not be located")
    store_route = route_match.group(1)
    if "products = sorted(all_active_products" not in store_route:
        fail("public storefront still hides active products outside their availability window")
    if "featured = [p for p in all_active_products if p.is_featured]" not in store_route:
        fail("featured products are still filtered out by the availability-time window")
    if "top_sellers = [p for p in all_active_products if p.is_top_seller]" not in store_route:
        fail("best sellers are still filtered out by the availability-time window")
    if "product_is_available_now=is_product_available_now" not in store_route:
        fail("storefront does not receive orderability status for active scheduled products")
    if "Not Available to Order Now" not in storefront or "Visible now • ordering follows its availability schedule" not in storefront:
        fail("storefront does not visibly distinguish scheduled products from orderable products")
    ok("all Active products stay visible; availability schedule controls ordering only")

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

    size_markers = [
        "size_schema = db.Column",
        "parse_product_size_schema",
        "product_price_for_options",
        "product_choice_groups",
        "Priced Sizes",
    ]
    combined_text = source + admin_template + cashier_template + storefront
    missing_sizes = [marker for marker in size_markers if marker not in combined_text]
    if missing_sizes:
        fail("priced product-size support is incomplete: " + ", ".join(missing_sizes))
    ok("product sub-sizes can carry server-validated selling prices")

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

    customer_dashboard_html = (TEMPLATES / "customer_dashboard.html").read_text(encoding="utf-8")
    if "Menu Vote & Rankings" in customer_dashboard_html or 'href="#menuVote"' in customer_dashboard_html or "/portal/menu-vote/" in customer_dashboard_html:
        fail("Customer Portal still exposes the retired menu-voting/rankings UI")
    if "MENU VOTES • MONTH" in admin_template or "Menu Vote Candidates & Rankings" in admin_template:
        fail("Master Admin still exposes the retired menu-voting/rankings UI")
    if "ensure_menu_vote_candidate(suggestion_text" in source:
        fail("free-text customer suggestions are still converted into vote/product candidates")
    if "ensure_default_promos()\n        ensure_menu_vote_candidates()" in source:
        fail("startup still auto-populates retired menu vote candidates")
    for marker in ["What would you like to buy from our shop?", "Customer entries stay exactly as free-text requests"]:
        if marker not in customer_dashboard_html + admin_template:
            fail(f"free-text suggestion workflow is missing: {marker}")
    ok("customer feedback is free-text only; voting/rankings UI is retired without deleting legacy data")

    loyalty_template = TEMPLATES / "loyalty_card_portal.html"
    if not loyalty_template.exists():
        fail("templates/loyalty_card_portal.html is missing")
    loyalty_html = loyalty_template.read_text(encoding="utf-8")
    loyalty_partial = TEMPLATES / "_loyalty_card_pair.html"
    if not loyalty_partial.exists():
        fail("templates/_loyalty_card_pair.html is missing")
    loyalty_partial_html = loyalty_partial.read_text(encoding="utf-8")
    loyalty_css_path = STATIC / "loyalty-card.css"
    if not loyalty_css_path.exists():
        fail("static/loyalty-card.css is missing")
    loyalty_css = loyalty_css_path.read_text(encoding="utf-8")
    loyalty_bundle = loyalty_html + customer_dashboard_html + loyalty_partial_html + loyalty_css + source
    loyalty_markers = [
        "@app.route('/admin/loyalty-cards')",
        "@app.route('/admin/loyalty-cards/<int:cust_id>/save'",
        "LOYALTY_CARD_THEMES",
        "qr_svg_data_url",
        "card_theme = db.Column",
        "customer_profile_image_from_request",
    ]
    missing_loyalty = [marker for marker in loyalty_markers if marker not in source]
    if missing_loyalty:
        fail("loyalty-card printing portal is incomplete: " + ", ".join(missing_loyalty))
    for marker in ["pink-classic", "cafe-cream", "midnight-gold", "mint-fresh", "purple-craft", "85.6 × 54 mm", "Print Front + Back"]:
        if marker not in loyalty_bundle:
            fail(f"loyalty-card portal UI is missing: {marker}")
    for marker in ["card_logo_scale", "card_photo_scale", "card_qr_scale", "card_text_scale", "card_info_scale", "Element Sizes", "--logo-scale", "--photo-scale", "--qr-scale", "--text-scale", "--info-scale"]:
        if marker not in loyalty_bundle:
            fail(f"loyalty-card element-size controls are incomplete: {marker}")
    if "{% include '_loyalty_card_pair.html' %}" not in loyalty_html or "{% include '_loyalty_card_pair.html' %}" not in customer_dashboard_html:
        fail("customer preview and admin print portal are not using the same loyalty-card renderer")
    if "url_for('admin_loyalty_cards')" not in admin_template:
        fail("Master Admin does not link to the Loyalty Card Printing portal")
    if 'type="file" name="profile_photo"' not in customer_dashboard_html or 'enctype="multipart/form-data"' not in customer_dashboard_html:
        fail("Customer Portal does not allow phone/gallery profile photo uploads")
    customer_login_html = (TEMPLATES / "customer_login.html").read_text(encoding="utf-8")
    if "Mobile Number or Card ID" not in customer_login_html or "card_hint" not in customer_login_html:
        fail("printed loyalty-card QR cannot prefill the member Card ID at login")
    for marker in ["@app.route('/portal/card-theme'", "loyalty_card_themes=LOYALTY_CARD_THEMES", "Choose My Loyalty Card Theme"]:
        if marker not in source + customer_dashboard_html:
            fail(f"customer loyalty-card theme chooser is missing: {marker}")
    if "fb.com/macleens" not in loyalty_partial_html:
        fail("printed loyalty card is missing fb.com/macleens")
    if "POINTS" in loyalty_partial_html.upper() or "Earn 1 point per" in loyalty_partial_html:
        fail("printed loyalty card still contains points/balance text instead of the approved points-free card design")
    ok("loyalty-card printer uses one shared landscape renderer, five themes, per-element size controls, member QR, gallery photo upload, and fb.com/macleens")

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
    if "shareStoreLink" not in storefront or "food-share-btn" not in storefront:
        fail("Food House storefront/product sharing controls are missing")
    if "event.target.closest('.food-share-btn')" not in storefront:
        fail("Food House storefront is missing the safe delegated product Share handler")
    if 'data-share-title="{{ p.name|e }}"' not in storefront or "data-share-url=" not in storefront:
        fail("Food House product cards are not using safe share data attributes")
    if "onclick='shareProductLink(" in storefront or 'onclick="shareProductLink(' in storefront:
        fail("Food House product cards still use fragile inline Share JavaScript")
    product_detail_html = (TEMPLATES / "product_detail.html").read_text(encoding="utf-8")
    if "shareFoodProductSafe" not in product_detail_html or "food-share-btn" not in product_detail_html:
        fail("Food House product detail sharing control is missing")
    if "event.target.closest('.food-share-btn')" not in product_detail_html:
        fail("Food House product detail is missing the safe delegated Share handler")
    ok("Food House per-product Share buttons use safe delegated handlers with copy fallback")
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
        if "share-helper.js') }}?v=6" not in content:
            fail(f"{rel} does not load the latest share helper cache version")
    ok("Share menu uses Facebook popup + Gmail email, without WhatsApp/Telegram")

    # Social preview metadata: page-level shares must use branded header artwork,
    # while individual product pages may use the product image. This prevents
    # Facebook from guessing the first product card as the page thumbnail.
    social_food = ROOT / "static" / "social" / "foodhouse-share-header.png"
    social_craft = ROOT / "static" / "social" / "craft-share-header.png"
    if not social_food.exists() or not social_craft.exists():
        fail("branded social-share header images are missing")
    if "social/foodhouse-share-header.png" not in storefront or 'property="og:image"' not in storefront:
        fail("Food House page does not force the branded header as its social preview image")
    if "social/craft-share-header.png" not in craft_base or 'property="og:image"' not in craft_base:
        fail("Craft Shop page does not force the branded header as its social preview image")
    if 'property="og:url"' not in storefront or 'property="og:url"' not in craft_base:
        fail("page-level Open Graph canonical URLs are missing")
    if 'property="og:type" content="product"' not in product_detail_html or 'property="og:type" content="product"' not in craft_detail:
        fail("individual product pages are missing product-specific social metadata")
    ok("page shares use branded header thumbnails; product shares keep product-specific previews")

    header_section = admin_template[:5000]
    if "url_for('craft_admin_dashboard')" in header_section:
        fail("master admin header still exposes a Craft Shop admin shortcut; Craft Admin should be direct-link only")
    ok("Craft Shop keeps legacy UI, per-IP views/likes/comments tracking, sharing, cashier sync, and direct-link-only admin access")


    # AI Marketing: Gemini Free by default, optional OpenAI/local template,
    # with manual Facebook Page/Group posting and no Meta Developer dependency.
    marketing_template = (TEMPLATES / "marketing_admin.html")
    marketing_module = ROOT / "marketing_agent.py"
    if not marketing_template.exists() or not marketing_module.exists():
        fail("AI Marketing template/module is missing")
    marketing_html = marketing_template.read_text(encoding="utf-8")
    marketing_py = marketing_module.read_text(encoding="utf-8")
    marketing_markers = [
        "class MarketingGroup(db.Model):",
        "class MarketingPost(db.Model):",
        "@app.route('/admin/marketing')",
        "@app.route('/admin/marketing/facebook-page'",
        "@app.route('/admin/marketing/post/<int:post_id>/mark-posted'",
        "@app.route('/tasks/marketing/run'",
        "generate_ai_marketing_decision",
        "MARKETING_CRON_TOKEN",
        "GROUP_ASSIST",
        "disable_legacy_meta_connection",
    ]
    missing_marketing = [m for m in marketing_markers if m not in source]
    if missing_marketing:
        fail("AI Marketing integration markers are missing: " + ", ".join(missing_marketing))
    if "url_for('marketing_admin')" not in admin_template:
        fail("Master Admin does not link to AI Marketing")
    for marker in [
        "Macleen's AI Marketing", "Manual Facebook mode", "Facebook Page — Manual Posting Shortcut",
        "Joined Facebook Groups — Manual Posting", "Copy Post", "Mark Posted",
        "Gemini Free (Recommended)", "Smart Template — No API", "Generate Marketing Draft",
    ]:
        if marker not in marketing_html:
            fail(f"AI Marketing UI is missing: {marker}")
    forbidden_meta = ["META_APP_ID", "META_APP_SECRET", "pages_manage_posts", "marketing_facebook_connect", "publish_page_link("]
    for marker in forbidden_meta:
        if marker in source or marker in marketing_py or marker in marketing_html:
            fail(f"Legacy Meta API integration is still exposed: {marker}")
    if "https://generativelanguage.googleapis.com/v1beta/interactions" not in marketing_py or "x-goog-api-key" not in marketing_py:
        fail("Gemini Interactions API integration is missing")
    if '"mime_type": "application/json"' not in marketing_py or "gemini-3.5-flash-lite" not in marketing_py:
        fail("Gemini structured-output/default-model configuration is missing")
    if "generate_template_marketing_decision" not in marketing_py or "smart-template-fallback" not in marketing_py:
        fail("No-cost smart-template fallback is missing")
    if "https://api.openai.com/v1/responses" not in marketing_py or '"type": "json_schema"' not in marketing_py:
        fail("Optional OpenAI structured-output integration is missing")
    render_yaml = (ROOT / "render.yaml").read_text(encoding="utf-8")
    if "GEMINI_API_KEY" not in render_yaml or "GEMINI_MARKETING_MODEL" not in render_yaml:
        fail("Render Gemini environment placeholders are missing")
    if "META_APP_ID" in render_yaml or "META_APP_SECRET" in render_yaml or "META_GRAPH_VERSION" in render_yaml:
        fail("Render still contains obsolete Meta API environment placeholders")
    if "publish_marketing_post" in source or "AUTO_PUBLISH" in source:
        fail("Automatic Facebook publishing is still present; this build must stay manual-only")
    reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    if "requests" not in reqs or "tzdata" not in reqs:
        fail("AI Marketing/Windows timezone runtime dependencies are missing from requirements.txt")
    if "cryptography" in reqs:
        fail("Obsolete Meta-token cryptography dependency is still present")
    ok("AI Marketing uses Gemini Free with local fallback and manual-only Facebook Page/Group posting")

    print("\nPRE-DEPLOY CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
