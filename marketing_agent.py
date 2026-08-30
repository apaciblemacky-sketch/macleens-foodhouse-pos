import base64
import hashlib
import json
import os
import re
from datetime import datetime
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
META_GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v25.0")
META_GRAPH_BASE = f"https://graph.facebook.com/{META_GRAPH_VERSION}"
META_DIALOG_BASE = f"https://www.facebook.com/{META_GRAPH_VERSION}/dialog/oauth"


def _fernet(secret_key: str) -> Fernet:
    digest = hashlib.sha256((secret_key or "").encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str, secret_key: str) -> str:
    if not value:
        return ""
    return _fernet(secret_key).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str, secret_key: str) -> str:
    if not value:
        return ""
    try:
        return _fernet(secret_key).decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def openai_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def meta_configured() -> bool:
    return bool(os.environ.get("META_APP_ID") and os.environ.get("META_APP_SECRET"))


def meta_login_url(redirect_uri: str, state: str) -> str:
    params = {
        "client_id": os.environ.get("META_APP_ID", ""),
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "pages_show_list,pages_read_engagement,pages_manage_posts",
        "response_type": "code",
    }
    return f"{META_DIALOG_BASE}?{urlencode(params)}"


def _meta_get(path: str, params=None, token: str = "", timeout: int = 20):
    params = dict(params or {})
    if token:
        params["access_token"] = token
    response = requests.get(f"{META_GRAPH_BASE}/{path.lstrip('/')}", params=params, timeout=timeout)
    data = response.json() if response.content else {}
    if not response.ok:
        message = ((data.get("error") or {}).get("message") if isinstance(data, dict) else None) or response.text
        raise RuntimeError(f"Meta API error: {message}")
    return data


def _meta_post(path: str, data=None, token: str = "", timeout: int = 25):
    payload = dict(data or {})
    if token:
        payload["access_token"] = token
    response = requests.post(f"{META_GRAPH_BASE}/{path.lstrip('/')}", data=payload, timeout=timeout)
    result = response.json() if response.content else {}
    if not response.ok:
        message = ((result.get("error") or {}).get("message") if isinstance(result, dict) else None) or response.text
        raise RuntimeError(f"Meta API error: {message}")
    return result


def list_managed_pages(user_token: str):
    return _meta_get(
        "me/accounts",
        {"fields": "id,name,access_token,tasks", "limit": 100},
        token=user_token,
    ).get("data", [])


def exchange_meta_code(code: str, redirect_uri: str):
    short = _meta_get(
        "oauth/access_token",
        {
            "client_id": os.environ.get("META_APP_ID", ""),
            "client_secret": os.environ.get("META_APP_SECRET", ""),
            "redirect_uri": redirect_uri,
            "code": code,
        },
    )
    user_token = short.get("access_token", "")
    if not user_token:
        raise RuntimeError("Meta did not return a user access token.")

    try:
        long_lived = _meta_get(
            "oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": os.environ.get("META_APP_ID", ""),
                "client_secret": os.environ.get("META_APP_SECRET", ""),
                "fb_exchange_token": user_token,
            },
        )
        user_token = long_lived.get("access_token") or user_token
    except Exception:
        # The normal short token is still enough to complete Page selection.
        pass

    return user_token, list_managed_pages(user_token)


def publish_page_link(page_id: str, page_access_token: str, message: str, link: str):
    if not page_id or not page_access_token:
        raise RuntimeError("No active Facebook Page connection.")
    payload = {"message": message.strip()}
    if link:
        payload["link"] = link
    return _meta_post(f"{page_id}/feed", payload, token=page_access_token)


def test_page_token(page_id: str, page_access_token: str):
    return _meta_get(page_id, {"fields": "id,name"}, token=page_access_token)


def _extract_output_text(payload: dict) -> str:
    texts = []
    for item in payload.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content", []) or []:
            if part.get("type") == "output_text" and part.get("text"):
                texts.append(part["text"])
    return "\n".join(texts).strip()


def generate_ai_marketing_decision(context: dict, business_hint: str = "AUTO", post_type_hint: str = "AUTO", group_context=None):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured in Render.")

    model = os.environ.get("OPENAI_MARKETING_MODEL", "gpt-5.5").strip() or "gpt-5.5"
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "should_post": {"type": "boolean"},
            "business": {"type": "string", "enum": ["FOODHOUSE", "CRAFT"]},
            "post_type": {
                "type": "string",
                "enum": [
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
                ],
            },
            "source_kind": {"type": "string", "enum": ["PRODUCT", "CRAFT_ITEM", "PAGE"]},
            "source_id": {"type": ["integer", "null"]},
            "caption": {"type": "string", "minLength": 1, "maxLength": 1800},
            "reason": {"type": "string", "minLength": 1, "maxLength": 600},
        },
        "required": ["should_post", "business", "post_type", "source_kind", "source_id", "caption", "reason"],
    }

    instructions = """
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

    input_payload = {
        "today": datetime.now().astimezone().isoformat(),
        "business_hint": business_hint,
        "post_type_hint": post_type_hint,
        "group": group_context or None,
        "business_context": context,
    }

    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "instructions": instructions,
            "input": json.dumps(input_payload, ensure_ascii=False),
            "max_output_tokens": 900,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "macleens_marketing_post",
                    "strict": True,
                    "schema": schema,
                }
            },
        },
        timeout=50,
    )
    payload = response.json() if response.content else {}
    if not response.ok:
        message = ((payload.get("error") or {}).get("message") if isinstance(payload, dict) else None) or response.text
        raise RuntimeError(f"OpenAI API error: {message}")
    text = _extract_output_text(payload)
    if not text:
        raise RuntimeError("OpenAI returned no marketing decision text.")
    try:
        decision = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI returned an invalid marketing decision.") from exc
    decision["model"] = model
    return decision


def extract_peso_amounts(text: str):
    amounts = []
    for raw in re.findall(r"(?:₱|PHP\s*)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text or "", flags=re.IGNORECASE):
        try:
            amounts.append(round(float(raw.replace(",", "")), 2))
        except ValueError:
            pass
    return amounts
