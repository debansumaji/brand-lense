"""Product information extraction using a deterministic demo mode or Anthropic."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from errors import AppError
from models import ProductData
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - only relevant when API mode lacks the optional package
    Anthropic = None  # type: ignore[assignment,misc]


load_dotenv()

CORE_FIELDS = ("price", "battery_hours", "anc", "warranty_years")
RETRY_MESSAGE = "Your last reply was not valid JSON matching the schema. Return only the JSON."


def _normalise_for_search(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


def filter_evidence(evidence: list[str], page_text: str) -> list[str]:
    """Keep only evidence snippets that occur in the supplied page text."""

    page = _normalise_for_search(page_text)
    filtered: list[str] = []
    seen: set[str] = set()
    for item in evidence:
        if not isinstance(item, str):
            continue
        snippet = re.sub(r"\s+", " ", item).strip()
        key = snippet.casefold()
        if snippet and key not in seen and _normalise_for_search(snippet) in page:
            filtered.append(snippet)
            seen.add(key)
    return filtered


def strip_json_fences(text: str) -> str:
    """Remove accidental Markdown JSON fences from a model response."""

    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```\s*(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    return cleaned.strip()


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse the first JSON object in a model response."""

    cleaned = strip_json_fences(text)
    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("No JSON object was found in the model response.")


def _format_number(value: str) -> float:
    number = float(value.replace(",", ""))
    return int(number) if number.is_integer() else number


def _first_match(pattern: str, text: str, flags: int = re.IGNORECASE) -> re.Match[str] | None:
    return re.search(pattern, text, flags)


def _mock_product_name(page_text: str) -> str | None:
    titled = _first_match(r"(?im)^\s*(?:title|product\s+name|name)\s*:\s*(.+?)\s*$", page_text)
    if titled:
        name = titled.group(1).strip().split(" | ", 1)[0].strip()
        if name:
            return name
    headphone = _first_match(r"(?i)([A-Z][\w&+ -]{2,80}\bHeadphones)\b", page_text)
    return headphone.group(1).strip() if headphone else None


def _mock_extract(page_text: str) -> ProductData:
    text = page_text or ""
    lowered = text.casefold()
    evidence: list[str] = []
    caveats: list[str] = []

    product_name = _mock_product_name(text)
    if product_name:
        evidence.append(product_name)

    brand_match = _first_match(r"(?im)^\s*brand\s*:\s*([^\n]+)", text)
    brand = brand_match.group(1).strip() if brand_match else None
    if brand:
        evidence.append(brand)

    price_match = _first_match(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)", text)
    foreign_price = _first_match(r"(?:[$€£]|USD|EUR|GBP)\s*[\d,]+(?:\.\d+)?", text)
    price = _format_number(price_match.group(1)) if price_match else None
    if price_match:
        evidence.append(price_match.group(0))
    elif foreign_price:
        caveats.append("The listed price is not in INR, so price was left unknown.")

    hours_match = _first_match(r"\b(\d+(?:\.\d+)?)\s*(hours?|hrs?|h)\b", text)
    battery_hours = _format_number(hours_match.group(1)) if hours_match else None
    if hours_match:
        evidence.append(hours_match.group(0))
        prefix = text[max(0, hours_match.start() - 12) : hours_match.start()].casefold()
        if re.search(r"\bup\s+to\s*$", prefix):
            shown_hours = hours_match.group(1)
            caveats.append(
                f"Battery life is stated as 'up to {shown_hours} hours', not a guaranteed figure"
            )

    active_anc = _first_match(r"\bactive\s+noise\s+cancellation\b|\bANC\b|\bENC\s*[- ]\s*for\s+music\b", text)
    no_anc = _first_match(
        r"\b(?:no|without|lacks?|does\s+not\s+include|not\s+supported)\s+(?:active\s+noise\s+cancellation|ANC)\b"
        r"|\b(?:active\s+noise\s+cancellation|ANC)\s+(?:is\s+)?(?:not\s+supported|not\s+included|not\s+mentioned|absent)\b",
        text,
    )
    passive = _first_match(r"\bpassive(?:\s+noise)?\s+isolation\b", text)
    enc = _first_match(r"\bENC\b", text)
    anc: bool | None
    if active_anc and not no_anc:
        anc = True
        evidence.append(active_anc.group(0))
    elif no_anc or passive:
        anc = False
        evidence.append((no_anc or passive).group(0))
    else:
        anc = None
    if enc and not active_anc:
        caveats.append("ENC is present, but call-only microphone noise reduction is not ANC.")
        evidence.append(enc.group(0))

    warranty_match = _first_match(
        r"(?i)(?:(\d+(?:\.\d+)?)\s*(years?|yrs?|months?|mos?)\s*(?:limited\s+)?warranty|"
        r"warranty\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(years?|yrs?|months?|mos?))",
        text,
    )
    warranty_years: float | None = None
    if warranty_match:
        amount = warranty_match.group(1) or warranty_match.group(3)
        unit = (warranty_match.group(2) or warranty_match.group(4)).casefold()
        warranty_years = _format_number(amount)
        if unit.startswith("month") or unit.startswith("mo"):
            warranty_years = warranty_years / 12
        evidence.append(warranty_match.group(0))

    bluetooth_match = _first_match(r"\bBluetooth\s*([0-9]+(?:\.[0-9]+)?)\b", text)
    bluetooth_version = bluetooth_match.group(1) if bluetooth_match else None
    if bluetooth_match:
        evidence.append(bluetooth_match.group(0))

    category = "Headphones" if "headphone" in lowered else None
    return ProductData(
        product_name=product_name,
        brand=brand,
        category=category,
        price=price,
        battery_hours=battery_hours,
        anc=anc,
        warranty_years=warranty_years,
        bluetooth_version=bluetooth_version,
        specifications={},
        evidence=evidence,
        caveats=caveats,
        unknown_fields=[],
    )


def _post_process(product: ProductData, page_text: str) -> ProductData:
    product.evidence = filter_evidence(product.evidence, page_text)
    product.unknown_fields = [field for field in CORE_FIELDS if getattr(product, field) is None]
    return product


def _is_mock_mode() -> bool:
    return os.getenv("USE_MOCK_AI", "false").strip().casefold() == "true" or not os.getenv(
        "ANTHROPIC_API_KEY", ""
    ).strip()


def _api_error() -> AppError:
    return AppError(
        "AI_FAILED",
        "The AI service could not extract product details right now. Please try again.",
        502,
    )


def _response_text(response: Any) -> str:
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content or []:
        value = getattr(block, "text", None)
        if value is None and isinstance(block, dict):
            value = block.get("text")
        if value:
            parts.append(str(value))
    return "\n".join(parts)


def _request_from_anthropic(client: Any, page_text: str, retry_response: str | None = None) -> str:
    messages: list[dict[str, str]] = [
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(page_text=page_text)},
    ]
    if retry_response is not None:
        messages.extend(
            [
                {"role": "assistant", "content": retry_response},
                {"role": "user", "content": RETRY_MESSAGE},
            ]
        )
    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        system=SYSTEM_PROMPT,
        messages=messages,
        temperature=0,
        max_tokens=1500,
    )
    return _response_text(response)


def _extract_api_product(page_text: str) -> ProductData:
    if Anthropic is None:
        raise _api_error()
    try:
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    except Exception as exc:
        raise _api_error() from exc

    try:
        first_response = _request_from_anthropic(client, page_text)
    except Exception as exc:
        raise _api_error() from exc

    try:
        return ProductData.model_validate(extract_json_object(first_response))
    except (ValueError, ValidationError):
        try:
            retry_response = _request_from_anthropic(client, page_text, first_response)
            return ProductData.model_validate(extract_json_object(retry_response))
        except Exception as second_error:
            raise _api_error() from second_error


def extract_product(page_text: str) -> ProductData:
    """Extract product facts from page text using mock mode or Anthropic."""

    if _is_mock_mode():
        return _post_process(_mock_extract(page_text), page_text)
    return _post_process(_extract_api_product(page_text), page_text)


__all__ = [
    "extract_json_object",
    "extract_product",
    "filter_evidence",
    "strip_json_fences",
]
