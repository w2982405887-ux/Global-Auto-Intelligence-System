from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EffectivePeriod(BaseModel):
    model_config = ConfigDict(frozen=True)

    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> "EffectivePeriod":
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")
        return self


# ── Evidence Layer ──────────────────────────────────────────────────


class RuleReference(BaseModel):
    """Pointer to the database rule record that drove a result."""
    rule_id: str | None = None           # vehicle_tariff_rate_line_id / rule_card_id
    rule_type: str | None = None         # "TARIFF_RATE" | "INCENTIVE_PROGRAM" | "DOMESTIC_TAX_RULE"
    rule_description: str | None = None  # human-readable


class SourceLocator(BaseModel):
    """Precise location within an official document."""
    locator_type: str = ""     # "HS_CODE" | "TABLE" | "PAGE" | "SECTION" | "SCHEDULE"
    locator_value: str = ""    # "Third Schedule / HS 8703801700" | "p.56"


class SourceReferenceSummary(BaseModel):
    """Lightweight source reference returned with every tax result."""
    source_id: str = ""                                     # document source_code
    document_title: str = ""
    authority_name: str = ""
    document_number: str | None = None
    source_type: str = ""                                   # "TARIFF_SCHEDULE" | "GAZETTE" | ...
    official_url: str | None = None
    locator: SourceLocator = Field(default_factory=SourceLocator)
