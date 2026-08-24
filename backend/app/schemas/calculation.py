from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ccu_code: str = Field(pattern=r"^CCU-[A-Z0-9-]+$")
    customs_value: Decimal = Field(ge=0)
    selected_mapping_codes: dict[str, str]
    excise_amount: Decimal | None = Field(default=None, ge=0)
    additional_landed_cost: Decimal = Field(default=Decimal("0"), ge=0)
    enterprise_inputs_complete: bool = False
    gri_2a_review_complete: bool = False


class PreferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proof_valid: bool = False
    origin_rule_compliance_confirmed: bool = False
    nomenclature_correlation_confirmed: bool = True
    enterprise_reviewed: bool = False
    simulation_only: bool = False


class ProfitComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sales_revenue: Decimal | None = Field(default=None, ge=0)
    non_import_costs: Decimal | None = Field(default=None, ge=0)
    recoverable_sst_fraction: Decimal = Field(default=Decimal("0"), ge=0, le=1)


class MalaysiaComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    import_date: date
    currency_code: str = Field(default="MYR", pattern=r"^[A-Z]{3}$")
    requested_regimes: tuple[str, ...] = ("MFN", "ACFTA", "RCEP")
    baseline_regime: str = "MFN"
    allow_mfn_fallback: bool = True
    items: tuple[ItemComparisonInput, ...]
    eligibility: dict[str, PreferenceInput] = Field(default_factory=dict)
    profit: ProfitComparisonInput = Field(default_factory=ProfitComparisonInput)

    @field_validator("requested_regimes")
    @classmethod
    def validate_regimes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {"MFN", "ACFTA", "RCEP"}
        if not value:
            raise ValueError("At least one regime is required")
        invalid = set(value) - allowed
        if invalid:
            raise ValueError(f"Unsupported Malaysia regimes: {sorted(invalid)}")
        return value
