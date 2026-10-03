import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import ai_agent
from errors import AppError
from models import ProductData


DEMO_DIR = Path(__file__).parents[1] / "demo_pages"


def demo_text(name: str) -> str:
    from scraper import extract_text_from_html

    html = (DEMO_DIR / name).read_text(encoding="utf-8")
    return extract_text_from_html(html)


def test_match_demo_mock_extraction(monkeypatch):
    monkeypatch.setenv("USE_MOCK_AI", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    product = ai_agent.extract_product(demo_text("demo_match.html"))

    assert product.price == 1799
    assert product.battery_hours == 50
    assert product.anc is True
    assert product.warranty_years == 1


def test_noanc_demo_mock_extraction(monkeypatch):
    monkeypatch.setenv("USE_MOCK_AI", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    product = ai_agent.extract_product(demo_text("demo_noanc.html"))

    assert product.price == 1499
    assert product.anc is False


def test_missing_demo_marks_warranty_unknown_and_up_to_caveat(monkeypatch):
    monkeypatch.setenv("USE_MOCK_AI", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    product = ai_agent.extract_product(demo_text("demo_missing.html"))

    assert product.battery_hours == 45
    assert product.warranty_years is None
    assert "warranty_years" in product.unknown_fields
    assert any("up to" in caveat.casefold() for caveat in product.caveats)


def test_filter_evidence_drops_fabricated_snippets():
    evidence = ai_agent.filter_evidence(
        ["Bluetooth 5.3", "This fabricated claim is absent"],
        "The product supports Bluetooth 5.3.",
    )

    assert evidence == ["Bluetooth 5.3"]


def test_json_fence_and_first_object_are_parsed():
    response = '```json\nPreamble ignored\n{"price": 1799, "evidence": []}\n```'

    assert ai_agent.strip_json_fences(response).startswith("Preamble ignored")
    assert ai_agent.extract_json_object(response)["price"] == 1799


def test_invalid_first_api_response_retries_once(monkeypatch):
    monkeypatch.setenv("USE_MOCK_AI", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "test-model")

    responses = [
        SimpleNamespace(content=[SimpleNamespace(text="not json")]),
        SimpleNamespace(content=[SimpleNamespace(text=json.dumps({"price": 1799}))]),
    ]

    class FakeMessages:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return responses.pop(0)

    messages = FakeMessages()
    monkeypatch.setattr(ai_agent, "Anthropic", lambda **kwargs: SimpleNamespace(messages=messages))

    product = ai_agent.extract_product("Price: ₹1,799")

    assert product.price == 1799
    assert len(messages.calls) == 2
    assert messages.calls[1]["messages"][-1]["content"] == ai_agent.RETRY_MESSAGE
