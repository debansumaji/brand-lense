from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


MATCH_TEXT = """Title: XYZ Wireless Headphones
Brand: XYZ
Price: ₹1,799
50 Hours Playback
Active Noise Cancellation
1 Year Warranty"""
NO_ANC_TEXT = """Title: BassBoom Pro Headphones
Price: ₹1,499
60 hours playback
Passive noise isolation
1 year warranty"""
MISSING_TEXT = """Title: AirWave Neo Headphones
Price: ₹1,899
Up to 45 hours battery
ANC supported
Bluetooth 5.2"""


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_manual_text_can_be_submitted_without_a_url():
    response = client.post(
        "/analyze",
        json={
            "page_text": MATCH_TEXT,
            "requirements": {"budget": 2000, "battery_hours": 40, "anc": "required"},
        },
    )
    assert response.status_code == 200
    assert response.json()["source"]["mode"] == "manual_text"


def test_manual_text_takes_precedence_over_an_invalid_url():
    response = client.post(
        "/analyze",
        json={
            "url": "not-a-url",
            "page_text": MATCH_TEXT,
            "requirements": {"budget": 2000},
        },
    )
    assert response.status_code == 200
    assert response.json()["source"]["mode"] == "manual_text"


def test_happy_path_is_great_match_3_of_3():
    response = client.post(
        "/analyze",
        json={
            "url": "http://localhost:8000/demo/demo_match.html",
            "page_text": MATCH_TEXT,
            "requirements": {"budget": 2000, "battery_hours": 40, "anc": "required"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "GREAT_MATCH"
    assert body["passed"] == 3
    assert body["total"] == 3


def test_noanc_with_mandatory_anc_fails():
    response = client.post(
        "/analyze",
        json={
            "url": "http://localhost:8000/demo/demo_noanc.html",
            "page_text": NO_ANC_TEXT,
            "requirements": {"anc": "required", "mandatory": ["anc"]},
        },
    )
    assert response.status_code == 200
    assert response.json()["verdict"] == "MANDATORY_FAILED"


def test_nowarranty_is_unknown_when_warranty_is_required():
    response = client.post(
        "/analyze",
        json={
            "url": "http://localhost:8000/demo/demo_missing.html",
            "page_text": MISSING_TEXT,
            "requirements": {"warranty_years": 1},
        },
    )
    assert response.status_code == 200
    item = response.json()["comparison"][0]
    assert item["key"] == "warranty_years"
    assert item["status"] == "UNKNOWN"


def test_invalid_body_returns_422():
    response = client.post("/analyze", json={"url": "https://example.com"})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_BODY"

