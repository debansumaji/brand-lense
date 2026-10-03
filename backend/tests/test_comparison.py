from comparison import build_result
from models import ProductData, Requirements, Source


SOURCE = Source(mode="demo", chars_used=100)


def test_all_pass_is_great_match_3_of_3():
    result = build_result(Requirements(budget=2000, battery_hours=40, anc="required"), ProductData(price=1799, battery_hours=50, anc=True), SOURCE)
    assert result.verdict == "GREAT_MATCH"
    assert result.passed == 3
    assert result.total == 3
    assert result.score_percent == 100


def test_mandatory_anc_failure_wins():
    result = build_result(Requirements(anc="required", mandatory=["anc"]), ProductData(anc=False), SOURCE)
    assert result.verdict == "MANDATORY_FAILED"
    assert result.comparison[0].status == "FAIL"


def test_missing_warranty_is_unknown_not_fail_and_warns():
    result = build_result(Requirements(warranty_years=1), ProductData(warranty_years=None), SOURCE)
    assert result.comparison[0].status == "UNKNOWN"
    assert result.comparison[0].status != "FAIL"
    assert any(warning.type == "missing_info" for warning in result.warnings)


def test_non_mandatory_failure_is_partial_match():
    result = build_result(Requirements(budget=2000), ProductData(price=2500), SOURCE)
    assert result.verdict == "PARTIAL_MATCH"
    assert result.comparison[0].mandatory is False


def test_any_anc_is_excluded_from_total():
    result = build_result(Requirements(anc="any", budget=2000), ProductData(price=1800), SOURCE)
    assert result.total == 1
    assert all(item.key != "anc" for item in result.comparison)


def test_no_requirements_has_zero_score():
    result = build_result(Requirements(), ProductData(), SOURCE)
    assert result.total == 0
    assert result.passed == 0
    assert result.score_percent == 0


def test_up_to_battery_evidence_adds_hidden_catch_warning():
    result = build_result(Requirements(battery_hours=40), ProductData(battery_hours=50, evidence=["Battery life: up to 50 hours"]), SOURCE)
    assert any(warning.type == "hidden_catch" for warning in result.warnings)

