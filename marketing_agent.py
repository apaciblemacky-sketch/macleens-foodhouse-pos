import base64
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
    "OCCASION_ORDER",
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



def generate_marketing_caption(
    *,
    product_name: str,
    price_text: str = "",
    business: str = "FOODHOUSE",
    post_type: str = "PRODUCT_SPOTLIGHT",
    word_target: int = 80,
    tone: str = "FRIENDLY",
    language: str = "ENGLISH",
    emojis: bool = True,
    include_cta: bool = True,
    include_hashtags: bool = True,
    audience: str = "LOCAL_CUSTOMERS",
):
    """Generate a configurable Facebook caption using Gemini text only.

    No image-generation API is involved. If Gemini is unavailable, a useful
    deterministic caption is returned so the feature still works.
    """
    try:
        word_target = max(10, min(int(word_target or 80), 500))
    except (TypeError, ValueError):
        word_target = 80

    tone_map = {
        "FRIENDLY": "friendly, warm, natural, and approachable",
        "CASUAL": "casual, conversational, and relatable",
        "EXCITING": "energetic, enthusiastic, and attention-grabbing",
        "PROFESSIONAL": "clean, polished, and professional",
        "STUDENT": "budget-conscious, youthful, and campus-friendly",
        "URGENCY": "direct, action-oriented, and time-sensitive without inventing scarcity",
    }
    language_map = {
        "ENGLISH": "English",
        "FILIPINO": "Filipino/Tagalog",
        "MIXED": "natural Taglish (English + Filipino)",
    }
    audience_map = {
        "LOCAL_CUSTOMERS": "local customers around Binalbagan",
        "STUDENTS": "students and young customers",
        "FAMILIES": "families and households",
        "OFFICE_GROUPS": "office, school, and group-order customers",
        "EVENT_CUSTOMERS": "customers planning birthdays, meetings, fiestas, school events, or other occasions",
        "EVERYONE": "a broad local audience",
    }
    purpose_map = {
        "PRODUCT_SPOTLIGHT": "highlight the product and make people want to try it",
        "OCCASION_ORDER": "encourage advance and bulk orders for occasions and gatherings",
        "SLOW_SELLER": "give the product renewed attention without insulting or calling it a slow seller",
        "TOP_SELLER": "highlight that it is a customer favorite without inventing review counts",
        "NEW_OR_FEATURED": "introduce it as a featured choice without inventing a launch date",
        "LOYALTY": "thank customers and encourage another order",
        "ENGAGEMENT": "invite customers to respond or share their preference",
        "BRAND_AWARENESS": "build familiarity with Macleen's",
        "RESTOCK_OR_AVAILABILITY": "tell customers the item is available today without inventing stock quantities",
        "CRAFT_STORY": "highlight the craft item naturally",
        "VALUE_REMINDER": "emphasize affordability and everyday value without inventing discounts",
    }
    tone_text = tone_map.get(str(tone).upper(), tone_map["FRIENDLY"])
    lang_text = language_map.get(str(language).upper(), language_map["ENGLISH"])
    audience_text = audience_map.get(str(audience).upper(), audience_map["LOCAL_CUSTOMERS"])
    purpose_text = purpose_map.get(str(post_type).upper(), purpose_map["PRODUCT_SPOTLIGHT"])

    api_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if api_key:
        model = os.environ.get("GEMINI_MARKETING_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
        prompt = f"""
You are Macleen's Food House social-media copywriter in Binalbagan, Philippines.

Write ONE ready-to-post Facebook caption for:
Business: {business}
Product: {product_name}
Price: {price_text or "No verified price supplied"}
Purpose: {purpose_text}
Audience: {audience_text}
Tone: {tone_text}
Language: {lang_text}
Target length: approximately {word_target} words
Emojis: {"Yes, use a few natural emojis" if emojis else "No emojis"}
Call to action: {"Include a clear order/message CTA" if include_cta else "Do not add a CTA"}
Hashtags: {"Add 3-6 relevant hashtags at the end" if include_hashtags else "Do not add hashtags"}

Rules:
- Use only the supplied product name and verified price.
- Never invent discounts, stock quantities, ingredients, reviews, awards, schedules, delivery claims, or limited-time scarcity.
- Do not mention that you are AI.
- Do not add a title such as "Caption:".
- Make the result directly copyable into Facebook.
- Stay close to the requested word target.
"""
        try:
            response = requests.post(
                GEMINI_INTERACTIONS_URL,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "model": model,
                    "input": prompt.strip(),
                    "response_format": {"type": "text"},
                    "generation_config": {
                        "max_output_tokens": max(80, min(1200, word_target * 2)),
                        "temperature": 0.8,
                    },
                },
                timeout=55,
            )
            body = response.json() if response.content else {}
            if not response.ok:
                error = body.get("error") if isinstance(body, dict) else {}
                message = error.get("message") if isinstance(error, dict) else None
                raise RuntimeError(message or response.text)
            caption = _extract_gemini_output_text(body).strip()
            if caption:
                return {"caption": caption, "model": f"gemini:{model}"}
        except Exception as exc:
            fallback_note = f"Gemini unavailable ({type(exc).__name__})"
        else:
            fallback_note = "Gemini returned no caption."
    else:
        fallback_note = "Gemini key not configured."

    emoji = "✨ " if emojis else ""
    cta = " Message us to order!" if include_cta else ""
    hashtags = " #MacleensFoodHouse #Binalbagan" if include_hashtags else ""
    price_line = f" for {price_text}" if price_text else ""
    if str(language).upper() == "FILIPINO":
        caption = f"{emoji}Try ang {product_name}{price_line}! Perfect ito para sa {audience_text}. {purpose_text.capitalize()}.{cta}{hashtags}"
    elif str(language).upper() == "MIXED":
        caption = f"{emoji}Craving for {product_name}{price_line}? Perfect for {audience_text}. {purpose_text.capitalize()}!{cta}{hashtags}"
    else:
        caption = f"{emoji}Try {product_name}{price_line}! A great choice for {audience_text}. {purpose_text.capitalize()}.{cta}{hashtags}"
    return {"caption": caption, "model": "smart-template:caption", "fallback_note": fallback_note}

def extract_peso_amounts(text: str):
    amounts = []
    for raw in re.findall(r"(?:₱|PHP\s*)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text or "", flags=re.IGNORECASE):
        try:
            amounts.append(round(float(raw.replace(",", "")), 2))
        except ValueError:
            pass
    return amounts


def _template_website_analytics_analysis(payload: dict, fallback_note: str = ""):
    portals = payload.get("portals") or {}
    labels = {"STOREFRONT": "Food Storefront", "CRAFT": "Crafts", "DIGITAL": "Digital"}
    rows = []
    for key in ("STOREFRONT", "CRAFT", "DIGITAL"):
        summary = (portals.get(key) or {}).get("summary") or {}
        visits = int(summary.get("visits") or 0)
        uniques = int(summary.get("unique_daily_sum") or 0)
        trend = float(summary.get("trend_percent") or 0.0)
        peak = summary.get("peak_date") or "—"
        rows.append((key, visits, uniques, trend, peak))
    strongest = max(rows, key=lambda row: row[1]) if rows else ("STOREFRONT", 0, 0, 0, "—")
    weakest = min(rows, key=lambda row: row[1]) if rows else strongest
    improving = [row for row in rows if row[3] > 5]
    declining = [row for row in rows if row[3] < -5]
    parts = [
        f"Traffic summary: {labels.get(strongest[0], strongest[0])} has the most visits in this period ({strongest[1]:,}). "
        f"{labels.get(weakest[0], weakest[0])} has the fewest ({weakest[1]:,}).",
        "Unique visitors: " + "; ".join(f"{labels[k]} {u:,} daily uniques / {v:,} visits" for k,v,u,_,_ in rows) + ".",
    ]
    if improving:
        parts.append("Positive movement: " + ", ".join(f"{labels[k]} {trend:+.1f}%" for k,_,_,trend,_ in improving) + ".")
    if declining:
        parts.append("Needs attention: " + ", ".join(f"{labels[k]} {trend:+.1f}%" for k,_,_,trend,_ in declining) + ".")
    parts.append(
        "Suggested action: promote one clear product or offer from the weakest portal using a direct link, then compare visits and daily uniques over the next 7 days. "
        "For the strongest portal, keep the current traffic source but test a stronger call-to-action that moves visitors toward checkout or My Apps rather than chasing page views alone."
    )
    if fallback_note:
        parts.append(f"AI note: {fallback_note}.")
    return {"model": "smart-template:website-analytics", "analysis": "\n\n".join(parts)}


def analyze_website_analytics(payload: dict, provider: str = "AUTO"):
    """Analyze aggregate portal traffic only; no raw IP, customer, or personal data is sent."""
    provider = (provider or "AUTO").upper()
    prompt = (
        "You are a practical web analytics adviser for Macleen's Food House, Crafts, and Digital in the Philippines. "
        "Analyze only the supplied aggregate daily visits and unique-visitor counts. Do not invent causes, revenue, demographics, or conversions. "
        "Return concise plain text with: Traffic Summary, What Changed, What to Test Next, and One Priority Action. "
        "Mention exact numbers where useful and distinguish visits from unique visitors.\n\nDATA:\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    attempts = []
    if provider in ("GEMINI", "AUTO") and gemini_configured():
        try:
            api_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
            model = os.environ.get("GEMINI_MARKETING_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
            response = requests.post(
                GEMINI_INTERACTIONS_URL,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={"model": model, "input": prompt, "response_format": {"type": "text"}},
                timeout=55,
            )
            body = response.json() if response.content else {}
            if not response.ok:
                raise RuntimeError(((body.get("error") or {}).get("message") if isinstance(body, dict) else None) or response.text)
            analysis = _extract_gemini_output_text(body)
            if not analysis:
                raise RuntimeError("Gemini returned no website analytics analysis.")
            return {"model": f"gemini:{model}", "analysis": analysis[:5000]}
        except Exception as exc:
            attempts.append(f"Gemini unavailable ({type(exc).__name__})")
    if provider in ("OPENAI", "AUTO") and openai_configured():
        try:
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            model = os.environ.get("OPENAI_MARKETING_MODEL", "gpt-5.5").strip() or "gpt-5.5"
            response = requests.post(
                OPENAI_RESPONSES_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "instructions": "Analyze aggregate website analytics accurately and concisely.", "input": prompt, "max_output_tokens": 900},
                timeout=50,
            )
            body = response.json() if response.content else {}
            if not response.ok:
                raise RuntimeError(((body.get("error") or {}).get("message") if isinstance(body, dict) else None) or response.text)
            analysis = _extract_openai_output_text(body)
            if not analysis:
                raise RuntimeError("OpenAI returned no website analytics analysis.")
            return {"model": f"openai:{model}", "analysis": analysis[:5000]}
        except Exception as exc:
            attempts.append(f"OpenAI unavailable ({type(exc).__name__})")
    return _template_website_analytics_analysis(payload, "; ".join(attempts))
