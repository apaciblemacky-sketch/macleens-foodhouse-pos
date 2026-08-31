import hashlib
import json
import os
import re
from datetime import datetime

import requests

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

MARKETING_POST_TYPES = [
    "PRODUCT_SPOTLIGHT",
    "SLOW_SELLER",
    "TOP_SELLER",
    "NEW_OR_FEATURED",
    "LOYALTY",
    "ENGAGEMENT",
    "BRAND_AWARENESS",
    "RESTOCK_OR_AVAILABILITY",
    "CRAFT_STORY",
    "VALUE_REMINDER",
]


def gemini_configured() -> bool:
    return bool((os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip())


def openai_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _marketing_schema(include_openai_constraints: bool = False):
    string_caption = {"type": "string"}
    string_reason = {"type": "string"}
    if include_openai_constraints:
        string_caption.update({"minLength": 1, "maxLength": 1800})
        string_reason.update({"minLength": 1, "maxLength": 600})
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "should_post": {"type": "boolean"},
            "business": {"type": "string", "enum": ["FOODHOUSE", "CRAFT"]},
            "post_type": {"type": "string", "enum": MARKETING_POST_TYPES},
            "source_kind": {"type": "string", "enum": ["PRODUCT", "CRAFT_ITEM", "PAGE"]},
            "source_id": {"type": ["integer", "null"]},
            "caption": string_caption,
            "reason": string_reason,
        },
        "required": ["should_post", "business", "post_type", "source_kind", "source_id", "caption", "reason"],
    }


def _marketing_instructions() -> str:
    return """
You are the autonomous marketing planner for Macleen's Food House and Macleen's Crafts in the Philippines.
Create one meaningful Facebook-ready post decision from ONLY the supplied business data.

Goals:
- Vary the post purpose and wording day by day; do not mechanically repeat yesterday's style.
- Prefer useful business reasons: available inventory, slow sellers, featured/new items, top sellers occasionally, loyalty/community engagement, or brand awareness.
- Keep captions warm, concise, natural, local-business friendly, and not spammy.
- Never invent a price, discount, stock count, schedule, customer quote, award, delivery promise, or promotion.
- Never claim urgency unless the supplied data supports it.
- Never promote an inactive or out-of-stock in-stock item.
- Respect recent-post history and avoid repeating a recently promoted product when alternatives exist.
- If there is no worthwhile/safe post today, set should_post=false and explain why.
- Do not put a URL in caption; the application attaches the verified link separately.
- Use at most four hashtags.
- For group-assisted posts, adapt the tone to the group's saved purpose/rules and avoid pretending the post was automatically published.
""".strip()


def _marketing_input_payload(context: dict, business_hint: str, post_type_hint: str, group_context=None):
    return {
        "today": datetime.now().astimezone().isoformat(),
        "business_hint": business_hint,
        "post_type_hint": post_type_hint,
        "group": group_context or None,
        "business_context": context,
    }


def _extract_openai_output_text(payload: dict) -> str:
    texts = []
    for item in payload.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content", []) or []:
            if part.get("type") == "output_text" and part.get("text"):
                texts.append(part["text"])
    return "\n".join(texts).strip()


def _extract_gemini_output_text(payload: dict) -> str:
    direct = payload.get("output_text") if isinstance(payload, dict) else None
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    texts = []
    for step in (payload.get("steps", []) if isinstance(payload, dict) else []) or []:
        if step.get("type") != "model_output":
            continue
        for part in step.get("content", []) or []:
            if part.get("type") == "text" and part.get("text"):
                texts.append(part["text"])
    return "\n".join(texts).strip()


def _generate_with_gemini(context: dict, business_hint: str, post_type_hint: str, group_context=None):
    api_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured in Render.")
    model = os.environ.get("GEMINI_MARKETING_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
    prompt = (
        _marketing_instructions()
        + "\n\nReturn the marketing decision as JSON matching the required schema.\n\nBUSINESS DATA:\n"
        + json.dumps(_marketing_input_payload(context, business_hint, post_type_hint, group_context), ensure_ascii=False)
    )
    response = requests.post(
        GEMINI_INTERACTIONS_URL,
        headers={
            "x-goog-api-key": api_key,
            "x-goog-api-client": "macleens-marketing/1.1.0",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": prompt,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": _marketing_schema(include_openai_constraints=False),
            },
        },
        timeout=55,
    )
    payload = response.json() if response.content else {}
    if not response.ok:
        if isinstance(payload, dict):
            error = payload.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else None
        else:
            message = None
        raise RuntimeError(f"Gemini API error: {message or response.text}")
    text = _extract_gemini_output_text(payload)
    if not text:
        raise RuntimeError("Gemini returned no marketing decision text.")
    try:
        decision = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini returned an invalid marketing decision.") from exc
    decision["model"] = f"gemini:{model}"
    return decision


def _generate_with_openai(context: dict, business_hint: str, post_type_hint: str, group_context=None):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured in Render.")

    model = os.environ.get("OPENAI_MARKETING_MODEL", "gpt-5.5").strip() or "gpt-5.5"
    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "instructions": _marketing_instructions(),
            "input": json.dumps(_marketing_input_payload(context, business_hint, post_type_hint, group_context), ensure_ascii=False),
            "max_output_tokens": 900,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "macleens_marketing_post",
                    "strict": True,
                    "schema": _marketing_schema(include_openai_constraints=True),
                }
            },
        },
        timeout=50,
    )
    payload = response.json() if response.content else {}
    if not response.ok:
        message = ((payload.get("error") or {}).get("message") if isinstance(payload, dict) else None) or response.text
        raise RuntimeError(f"OpenAI API error: {message}")
    text = _extract_openai_output_text(payload)
    if not text:
        raise RuntimeError("OpenAI returned no marketing decision text.")
    try:
        decision = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI returned an invalid marketing decision.") from exc
    decision["model"] = f"openai:{model}"
    return decision


def _stable_pick(items, seed_text: str):
    if not items:
        return None
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return items[int(digest[:12], 16) % len(items)]


def _money(value) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    if amount.is_integer():
        return f"₱{int(amount):,}"
    return f"₱{amount:,.2f}"


def generate_template_marketing_decision(context: dict, business_hint: str = "AUTO", post_type_hint: str = "AUTO", group_context=None, fallback_note: str = ""):
    """Offline/no-cost safety net. Uses only verified server context and never calls an AI API."""
    foods = list(context.get("foodhouse_products") or [])
    crafts = list(context.get("craft_items") or [])
    recent = list(context.get("recent_posts") or [])
    today = datetime.now().astimezone().date().isoformat()

    requested_business = (business_hint or "AUTO").upper()
    if requested_business in ("FOODHOUSE", "CRAFT"):
        business = requested_business
    else:
        if foods and not crafts:
            business = "FOODHOUSE"
        elif crafts and not foods:
            business = "CRAFT"
        else:
            recent_business = [str(p.get("business") or "").upper() for p in recent[:8]]
            food_count = recent_business.count("FOODHOUSE")
            craft_count = recent_business.count("CRAFT")
            if food_count != craft_count:
                business = "FOODHOUSE" if food_count < craft_count else "CRAFT"
            else:
                business = _stable_pick(["FOODHOUSE", "CRAFT"], f"business|{today}") or "FOODHOUSE"

    rows = foods if business == "FOODHOUSE" else crafts
    if not rows:
        other_business = "CRAFT" if business == "FOODHOUSE" else "FOODHOUSE"
        other_rows = crafts if other_business == "CRAFT" else foods
        if other_rows:
            business, rows = other_business, other_rows

    recent_pairs = {
        (str(p.get("source_kind") or "").upper(), p.get("source_id"))
        for p in recent[:18]
        if p.get("source_id") is not None
    }
    source_kind = "PRODUCT" if business == "FOODHOUSE" else "CRAFT_ITEM"
    fresh_rows = [r for r in rows if (source_kind, r.get("id")) not in recent_pairs] or rows

    requested_type = (post_type_hint or "AUTO").upper()
    if requested_type in MARKETING_POST_TYPES:
        post_type = requested_type
    else:
        recent_types = [str(p.get("post_type") or "").upper() for p in recent[:6]]
        if business == "FOODHOUSE":
            slow_exists = any(int(r.get("qty_30d") or 0) <= 1 for r in fresh_rows)
            featured_exists = any(r.get("featured") for r in fresh_rows)
            top_exists = any(r.get("top_seller") for r in fresh_rows)
            choices = ["PRODUCT_SPOTLIGHT", "VALUE_REMINDER", "ENGAGEMENT", "BRAND_AWARENESS"]
            if slow_exists:
                choices.append("SLOW_SELLER")
            if featured_exists:
                choices.append("NEW_OR_FEATURED")
            if top_exists:
                choices.append("TOP_SELLER")
        else:
            featured_exists = any(r.get("featured") for r in fresh_rows)
            top_exists = any(r.get("top_seller") for r in fresh_rows)
            choices = ["CRAFT_STORY", "PRODUCT_SPOTLIGHT", "VALUE_REMINDER", "ENGAGEMENT", "BRAND_AWARENESS"]
            if featured_exists:
                choices.append("NEW_OR_FEATURED")
            if top_exists:
                choices.append("TOP_SELLER")
        non_recent = [x for x in choices if x not in recent_types] or choices
        post_type = _stable_pick(non_recent, f"type|{business}|{today}") or "BRAND_AWARENESS"

    page_types = {"ENGAGEMENT", "BRAND_AWARENESS", "LOYALTY"}
    item = None
    if rows and post_type not in page_types:
        if post_type == "SLOW_SELLER" and business == "FOODHOUSE":
            item = min(fresh_rows, key=lambda r: (int(r.get("qty_30d") or 0), -int(r.get("stock") or 0), str(r.get("name") or "")))
        elif post_type == "TOP_SELLER":
            flagged = [r for r in fresh_rows if r.get("top_seller")]
            pool = flagged or fresh_rows
            if business == "FOODHOUSE":
                item = max(pool, key=lambda r: (int(r.get("qty_30d") or 0), int(r.get("likes") or 0)))
            else:
                item = max(pool, key=lambda r: (int(r.get("orders") or 0), int(r.get("likes") or 0), int(r.get("views") or 0)))
        elif post_type == "NEW_OR_FEATURED":
            item = _stable_pick([r for r in fresh_rows if r.get("featured")] or fresh_rows, f"featured|{today}|{business}")
        else:
            item = _stable_pick(fresh_rows, f"item|{today}|{business}|{post_type}")

    if item:
        name = str(item.get("name") or "our featured item")
        price = _money(item.get("price"))
        if business == "FOODHOUSE":
            variants = {
                "SLOW_SELLER": [
                    f"A little spotlight for {name} ✨ Enjoy it today for {price}. See what else is available at Macleen's Food House. #MacleensFoodHouse",
                    f"Have you tried {name} yet? 😊 It's available for {price}. Take a look at today's Macleen's Food House choices. #MacleensFoodHouse",
                ],
                "TOP_SELLER": [
                    f"Today's Macleen's pick: {name} — {price}. A simple favorite to add to your order today. #MacleensFoodHouse",
                    f"Craving something from Macleen's? {name} is available for {price}. Check today's menu and order when you're ready. #MacleensFoodHouse",
                ],
                "NEW_OR_FEATURED": [
                    f"Featured today at Macleen's Food House ✨ {name} is available for {price}. Check the menu for today's choices. #MacleensFoodHouse",
                    f"Put {name} on your food list today 😋 Available for {price} at Macleen's Food House. #MacleensFoodHouse",
                ],
                "RESTOCK_OR_AVAILABILITY": [
                    f"Available today: {name} for {price}. Check Macleen's Food House for current menu availability. #MacleensFoodHouse",
                ],
                "VALUE_REMINDER": [
                    f"Good food doesn't have to be complicated 💗 {name} is available for {price}. Browse Macleen's Food House for more choices. #MacleensFoodHouse",
                ],
            }
            options = variants.get(post_type) or [
                f"Today's food spotlight: {name} ✨ Available for {price} at Macleen's Food House. Check the menu and choose your next favorite. #MacleensFoodHouse",
                f"Something tasty for today: {name} — {price}. Browse Macleen's Food House for the rest of today's available choices. #MacleensFoodHouse",
            ]
        else:
            availability = str(item.get("availability") or "IN_STOCK").upper()
            availability_text = "Available for pre-order" if availability == "PREORDER" else "Available now"
            variants = {
                "CRAFT_STORY": [
                    f"A small craft with a lot of charm 🎀 {name} is {price}. {availability_text} from Macleen's Crafts. #MacleensCrafts",
                    f"Craft pick of the day ✨ {name} — {price}. {availability_text}. Browse Macleen's Crafts for more designs. #MacleensCrafts",
                ],
                "TOP_SELLER": [
                    f"Today's Craft pick: {name} 🎀 {price}. {availability_text} from Macleen's Crafts. #MacleensCrafts",
                ],
                "NEW_OR_FEATURED": [
                    f"Featured from Macleen's Crafts ✨ {name} is {price}. {availability_text}. #MacleensCrafts",
                ],
                "VALUE_REMINDER": [
                    f"A cute little gift idea 🎁 {name} is {price}. {availability_text} from Macleen's Crafts. #MacleensCrafts",
                ],
            }
            options = variants.get(post_type) or [
                f"Craft spotlight 🎀 {name} — {price}. {availability_text} from Macleen's Crafts. #MacleensCrafts",
                f"Looking for a small handmade-style gift? ✨ {name} is {price}. {availability_text} from Macleen's Crafts. #MacleensCrafts",
            ]
        caption = _stable_pick(options, f"caption|{today}|{business}|{item.get('id')}|{post_type}")
        reason = f"Selected {name} from currently available {business.title()} inventory and varied the post from recent marketing history."
        source_id = item.get("id")
    else:
        source_kind = "PAGE"
        source_id = None
        if business == "CRAFT":
            options = [
                "Which Macleen's Crafts design would you love to see next? 🎀 Browse the current collection and tell us your favorite. #MacleensCrafts",
                "A little creativity can brighten the day ✨ Take a look around Macleen's Crafts and see what's currently available. #MacleensCrafts",
                "Looking for a simple gift or something cute for yourself? 🎁 Browse Macleen's Crafts and discover the current collection. #MacleensCrafts",
            ]
        else:
            options = [
                "What are you craving today? 😋 Browse Macleen's Food House and check what's currently available. #MacleensFoodHouse",
                "Your next snack or meal might already be waiting 💗 Take a look at today's Macleen's Food House choices. #MacleensFoodHouse",
                "Food, drinks, and everyday favorites in one place ✨ Browse Macleen's Food House and see what's available today. #MacleensFoodHouse",
            ]
        caption = _stable_pick(options, f"page|{today}|{business}|{post_type}")
        reason = f"Chose a {post_type.replace('_', ' ').lower()} page post to vary the recent {business.title()} marketing mix."

    if group_context:
        reason += f" Draft is intended for the saved group '{group_context.get('name') or 'Facebook group'}'."
    if fallback_note:
        reason += f" {fallback_note}"

    return {
        "should_post": True,
        "business": business,
        "post_type": post_type,
        "source_kind": source_kind,
        "source_id": source_id,
        "caption": caption,
        "reason": reason[:600],
        "model": "smart-template-fallback",
    }


def generate_ai_marketing_decision(context: dict, business_hint: str = "AUTO", post_type_hint: str = "AUTO", group_context=None, provider: str = "GEMINI"):
    """Generate a marketing decision using the selected provider with a zero-cost local fallback.

    Provider behavior:
    - GEMINI (default): Gemini first, then smart-template fallback.
    - OPENAI: OpenAI first, then smart-template fallback.
    - AUTO: Gemini -> OpenAI -> smart-template fallback.
    - TEMPLATE: local smart-template generator only; no external API call.
    """
    provider = (provider or "GEMINI").strip().upper()
    if provider not in ("GEMINI", "OPENAI", "AUTO", "TEMPLATE"):
        provider = "GEMINI"

    attempts = []
    if provider in ("GEMINI", "AUTO") and gemini_configured():
        try:
            return _generate_with_gemini(context, business_hint, post_type_hint, group_context)
        except Exception as exc:
            attempts.append(f"Gemini unavailable ({type(exc).__name__})")

    if provider in ("OPENAI", "AUTO") and openai_configured():
        try:
            return _generate_with_openai(context, business_hint, post_type_hint, group_context)
        except Exception as exc:
            attempts.append(f"OpenAI unavailable ({type(exc).__name__})")

    if provider == "GEMINI" and not gemini_configured():
        attempts.append("Gemini key not configured")
    if provider == "OPENAI" and not openai_configured():
        attempts.append("OpenAI key not configured")
    if provider == "AUTO" and not gemini_configured() and not openai_configured():
        attempts.append("No external AI key configured")

    note = "Smart template fallback used."
    if attempts:
        note += " " + "; ".join(attempts) + "."
    return generate_template_marketing_decision(
        context,
        business_hint=business_hint,
        post_type_hint=post_type_hint,
        group_context=group_context,
        fallback_note=note,
    )


def extract_peso_amounts(text: str):
    amounts = []
    for raw in re.findall(r"(?:₱|PHP\s*)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text or "", flags=re.IGNORECASE):
        try:
            amounts.append(round(float(raw.replace(",", "")), 2))
        except ValueError:
            pass
    return amounts
