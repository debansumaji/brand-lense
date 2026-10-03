from pathlib import Path

import pytest

import scraper
from errors import AppError
from scraper import contains_block_marker, extract_text_from_html, fetch_product_text, validate_url


DEMO_DIR = Path(__file__).parents[1] / "demo_pages"


def read_demo(name: str) -> str:
    return (DEMO_DIR / name).read_text(encoding="utf-8")


def test_match_demo_extracts_structured_product_details():
    text = extract_text_from_html(read_demo("demo_match.html"))

    assert len(text) <= 12_000
    assert "XYZ Wireless Headphones" in text
    assert "₹1,799" in text
    assert "50 Hours Playback" in text
    assert "Active Noise Cancellation" in text
    assert "Bluetooth 5.3" in text
    assert "1 Year Warranty" in text


def test_noanc_demo_preserves_passive_noise_isolation_claim():
    text = extract_text_from_html(read_demo("demo_noanc.html"))

    assert "BassBoom Pro Headphones" in text
    assert "₹1,499" in text
    assert "60 hours playback" in text
    assert "Passive noise isolation" in text
    assert "Bluetooth 5.0" in text
    assert "1 year warranty" in text
    assert "ANC" not in text


def test_missing_demo_keeps_vague_battery_and_omits_warranty():
    text = extract_text_from_html(read_demo("demo_missing.html"))

    assert "AirWave Neo Headphones" in text
    assert "₹1,899" in text
    assert "Up to 45 hours" in text
    assert "ANC supported" in text
    assert "warranty" not in text.lower()


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("http://127.0.0.1", "BLOCKED_URL"),
        ("http://169.254.169.254", "BLOCKED_URL"),
        ("ftp://x", "INVALID_URL"),
        ("not a url", "INVALID_URL"),
    ],
)
def test_url_validator_rejects_invalid_or_private_destinations(url: str, code: str):
    with pytest.raises(AppError) as error:
        validate_url(url)

    assert error.value.code == code


def test_local_demo_url_is_allowed_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_LOCAL_DEMO", raising=False)
    validate_url("http://localhost:8000/demo/demo_match.html")


def test_local_demo_shortcut_reads_from_disk_without_http(monkeypatch):
    def fail_http_request(*args, **kwargs):
        raise AssertionError("local demo shortcut must not make an HTTP request")

    monkeypatch.setattr(scraper.requests, "get", fail_http_request)
    text, chars_used = fetch_product_text("http://127.0.0.1:8000/demo/demo_match.html")

    assert "XYZ Wireless Headphones" in text
    assert chars_used == len(text)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/demo/../.env",
        "http://localhost:8000/demo/%2e%2e%2f.env",
        "http://localhost:8000/demo/subdir/demo_match.html",
    ],
)
def test_local_demo_shortcut_rejects_traversal_and_nested_paths(url: str):
    with pytest.raises(AppError) as error:
        fetch_product_text(url)

    assert error.value.code == "BLOCKED_URL"


def test_captcha_marker_detection():
    assert contains_block_marker("Please complete the CAPTCHA to continue")
    assert contains_block_marker("Access Denied")
    assert contains_block_marker("Checking your browser: robot check")
    assert not contains_block_marker("XYZ Wireless Headphones")
