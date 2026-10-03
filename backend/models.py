from typing import Any, Literal

from pydantic import BaseModel, Field


class Requirements(BaseModel):
    category: str = "headphones"
    budget: float | None = None
    battery_hours: float | None = None
    anc: Literal["required", "not_required", "any"] = "any"
    usage: Literal["travel", "gaming", "office", "music"] | None = None
    warranty_years: float | None = None
    mandatory: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    url: str = ""
    page_text: str | None = None
    requirements: Requirements


class ProductData(BaseModel):
    product_name: str | None = None
    brand: str | None = None
    category: str | None = None
    price: float | None = None
    battery_hours: float | None = None
    anc: bool | None = None
    warranty_years: float | None = None
    bluetooth_version: str | None = None
    specifications: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    unknown_fields: list[str] = Field(default_factory=list)


class ComparisonItem(BaseModel):
    key: Literal["budget", "battery_hours", "anc", "warranty_years"]
    label: str
    requirement_text: str
    product_value_text: str
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    mandatory: bool
    reason: str


class Warning(BaseModel):
    type: Literal["mandatory_failed", "missing_info", "hidden_catch", "general"]
    message: str


class Source(BaseModel):
    mode: Literal["scraped", "manual_text", "demo"]
    chars_used: int


class AnalyzeResponse(BaseModel):
    product: ProductData
    comparison: list[ComparisonItem]
    passed: int
    total: int
    score_percent: int
    verdict: Literal[
        "GREAT_MATCH",
        "PARTIAL_MATCH",
        "MANDATORY_FAILED",
        "NEEDS_VERIFICATION",
    ]
    warnings: list[Warning]
    source: Source

