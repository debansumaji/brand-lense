from models import AnalyzeResponse, ComparisonItem, ProductData, Requirements, Source, Warning


def _format_money(value: float | None) -> str:
    if value is None:
        return "Not found"
    return f"₹{value:,.0f}"


def _format_number(value: float | None, unit: str) -> str:
    if value is None:
        return "Not found"
    return f"{value:g} {unit}"


def compare(requirements: Requirements, product: ProductData) -> list[ComparisonItem]:
    mandatory = set(requirements.mandatory)
    items: list[ComparisonItem] = []

    if requirements.budget is not None:
        if product.price is None:
            status = "UNKNOWN"
            reason = "Price was not found on the page, so this could not be verified."
        elif product.price <= requirements.budget:
            status = "PASS"
            reason = f"{_format_money(product.price)} is within your {_format_money(requirements.budget)} budget."
        else:
            status = "FAIL"
            reason = f"{_format_money(product.price)} is above your {_format_money(requirements.budget)} budget."
        items.append(ComparisonItem(key="budget", label="Budget", requirement_text=f"≤ {_format_money(requirements.budget)}", product_value_text=_format_money(product.price), status=status, mandatory="budget" in mandatory, reason=reason))

    if requirements.battery_hours is not None:
        if product.battery_hours is None:
            status = "UNKNOWN"
            reason = "Battery life was not found on the page, so this could not be verified."
        elif product.battery_hours >= requirements.battery_hours:
            status = "PASS"
            reason = f"{_format_number(product.battery_hours, 'hours')} meets your {requirements.battery_hours:g}-hour minimum."
        else:
            status = "FAIL"
            reason = f"{_format_number(product.battery_hours, 'hours')} is below your {requirements.battery_hours:g}-hour minimum."
        items.append(ComparisonItem(key="battery_hours", label="Battery life", requirement_text=f"≥ {requirements.battery_hours:g} hours", product_value_text=_format_number(product.battery_hours, "hours"), status=status, mandatory="battery_hours" in mandatory, reason=reason))

    if requirements.anc != "any":
        if requirements.anc == "not_required":
            status = "PASS"
            reason = "ANC is optional for this check."
        elif product.anc is None:
            status = "UNKNOWN"
            reason = "ANC was not found on the page, so this could not be verified."
        elif product.anc:
            status = "PASS"
            reason = "The product lists active noise cancellation."
        else:
            status = "FAIL"
            reason = "The product does not list active noise cancellation."
        items.append(ComparisonItem(key="anc", label="Noise cancellation", requirement_text="ANC required" if requirements.anc == "required" else "Not required", product_value_text="Yes" if product.anc is True else "No" if product.anc is False else "Not found", status=status, mandatory="anc" in mandatory, reason=reason))

    if requirements.warranty_years is not None:
        if product.warranty_years is None:
            status = "UNKNOWN"
            reason = "Warranty duration was not found on the page, so this could not be verified."
        elif product.warranty_years >= requirements.warranty_years:
            status = "PASS"
            reason = f"{_format_number(product.warranty_years, 'years')} meets your {requirements.warranty_years:g}-year minimum."
        else:
            status = "FAIL"
            reason = f"{_format_number(product.warranty_years, 'years')} is below your {requirements.warranty_years:g}-year minimum."
        items.append(ComparisonItem(key="warranty_years", label="Warranty", requirement_text=f"≥ {requirements.warranty_years:g} years", product_value_text=_format_number(product.warranty_years, "years"), status=status, mandatory="warranty_years" in mandatory, reason=reason))

    return items


def build_result(requirements: Requirements, product: ProductData, source: Source) -> AnalyzeResponse:
    items = compare(requirements, product)
    passed = sum(item.status == "PASS" for item in items)
    total = len(items)
    failed_mandatory = [item for item in items if item.status == "FAIL" and item.mandatory]
    unknown_mandatory = [item for item in items if item.status == "UNKNOWN" and item.mandatory]
    unknown_items = [item for item in items if item.status == "UNKNOWN"]

    if failed_mandatory:
        verdict = "MANDATORY_FAILED"
    elif unknown_items:
        verdict = "NEEDS_VERIFICATION"
    elif all(item.status == "PASS" for item in items):
        verdict = "GREAT_MATCH"
    else:
        verdict = "PARTIAL_MATCH"

    warnings = [Warning(type="mandatory_failed", message=f"{item.label} does not meet your deal-breaker.") for item in failed_mandatory]
    warnings.extend(Warning(type="missing_info", message=f"{item.label} needs verification because the page does not provide enough information.") for item in unknown_items)
    warnings.extend(Warning(type="hidden_catch", message=caveat) for caveat in product.caveats)
    if any(phrase in " ".join(product.evidence).lower() for phrase in ("up to", "upto", "claimed")):
        warnings.append(Warning(type="hidden_catch", message="Battery performance is expressed as a seller claim or an 'up to' figure."))
    warnings.append(Warning(type="general", message="Specs come from the seller's page; verify before buying."))

    return AnalyzeResponse(product=product, comparison=items, passed=passed, total=total, score_percent=round(passed / total * 100) if total else 0, verdict=verdict, warnings=warnings, source=source)

