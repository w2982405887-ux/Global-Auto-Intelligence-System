"""Malaysia domestic tax resolver — statutory rates + DB-backed in future.

CURRENT: Hardcoded seed data aligned with official Malaysian policy.
FUTURE: Query domestic_tax_rule table for rate + treatment + effective dates.

Key semantics (must NOT be conflated):
  NULL         — data missing, cannot determine
  0            — explicitly zero rate
  EXEMPT       — legal exemption pathway exists (may be conditional)
  NOT_AT_IMPORT — this tax is not collected at this stage (e.g. CKD excise)
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any, Literal

TaxCode = Literal[
    "IMPORT_DUTY",
    "EXCISE",
    "SALES_TAX",
    "IMPORT_SALES_TAX",
    "FINISHED_VEHICLE_SST",
]
TaxStage = Literal["AT_IMPORT", "LOCAL_ASSEMBLY"]
Treatment = Literal[
    "STATUTORY_RATE",
    "CONDITIONAL_EXEMPTION",
    "UNCONDITIONAL_EXEMPTION",
    "NOT_AT_IMPORT",
    "UNKNOWN",
]


@dataclass
class DomesticTaxRule:
    """One domestic tax rule row (seed data; future: DB table)."""
    country_iso2: str
    tax_code: TaxCode
    stage: TaxStage
    import_mode: str          # "CBU" | "CKD"
    powertrain: str | None    # None = applies to all
    displacement_min: int | None
    displacement_max: int | None
    statutory_rate: Decimal | None
    treatment: Treatment
    conditional: bool         # True → requires approval to activate
    approval_required: bool
    approval_authority: str | None
    effective_from: date
    effective_to: date | None
    source_description: str


# ═════════════════════════════════════════════════════════════════════
#  Seed data — aligned with Malaysian official policy as of 2026-07-31
# ═════════════════════════════════════════════════════════════════════

_BEV_CBU_EXCISE_NOTE = "BEV乘用车CBU消费税率（马来西亚国内税，不受FTA影响）"
_BEV_CBU_SST_NOTE = "BEV乘用车CBU销售税率（马来西亚国内税，不受FTA影响）"
_BEV_CKD_EXCISE_NOTE = "BEV本地组装消费税（本地成车阶段，不受FTA影响）"
_BEV_CKD_SST_NOTE = "BEV本地组装成车销售税（本地成车阶段，不受FTA影响）"
_ICE_CBU_EXCISE_NOTE = "ICE汽油CBU消费税按排量分档，需精确匹配车型"
_ICE_CKD_EXCISE_NOTE = "ICE本地组装消费税按排量和车型核定"
_SST_NOTE = "乘用车销售税率（马来西亚国内税，不受FTA影响）"
_CKD_IMPORT_SST_NOTE = (
    "CKD Pack在取得海关总监(DG)批准并全部直接用于制造时免进口销售税。"
    "实际豁免需结合Schedule C和具体审批确认。"
)

_SEED_RULES: list[DomesticTaxRule] = [
    # ── CBU EXCISE ──
    DomesticTaxRule("MY", "EXCISE", "AT_IMPORT", "CBU", "BEV", None, None,
                    Decimal("0.10"), "STATUTORY_RATE", False, False, None,
                    date(2020, 1, 1), None, _BEV_CBU_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "AT_IMPORT", "CBU", "FCEV", None, None,
                    Decimal("0.10"), "STATUTORY_RATE", False, False, None,
                    date(2020, 1, 1), None, _BEV_CBU_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "AT_IMPORT", "CBU", "ICE_GASOLINE", None, None,
                    None, "STATUTORY_RATE", False, False, None,
                    date(2020, 1, 1), None, _ICE_CBU_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "AT_IMPORT", "CBU", "ICE_DIESEL", None, None,
                    None, "STATUTORY_RATE", False, False, None,
                    date(2020, 1, 1), None, _ICE_CBU_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "AT_IMPORT", "CBU", "HEV", None, None,
                    None, "STATUTORY_RATE", False, False, None,
                    date(2020, 1, 1), None, _ICE_CBU_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "AT_IMPORT", "CBU", "PHEV", None, None,
                    None, "STATUTORY_RATE", False, False, None,
                    date(2020, 1, 1), None, _ICE_CBU_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "AT_IMPORT", "CBU", "EREV", None, None,
                    None, "STATUTORY_RATE", False, False, None,
                    date(2020, 1, 1), None, _ICE_CBU_EXCISE_NOTE),
    # ── CBU SALES TAX ──
    DomesticTaxRule("MY", "SALES_TAX", "AT_IMPORT", "CBU", None, None, None,
                    Decimal("0.10"), "STATUTORY_RATE", False, False, None,
                    date(2020, 1, 1), None, _SST_NOTE),
    # ── CKD EXCISE (NOT_AT_IMPORT) ──
    DomesticTaxRule("MY", "EXCISE", "LOCAL_ASSEMBLY", "CKD", "BEV", None, None,
                    Decimal("0.10"), "NOT_AT_IMPORT", False, False, None,
                    date(2020, 1, 1), None, _BEV_CKD_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "LOCAL_ASSEMBLY", "CKD", "FCEV", None, None,
                    Decimal("0.10"), "NOT_AT_IMPORT", False, False, None,
                    date(2020, 1, 1), None, _BEV_CKD_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "LOCAL_ASSEMBLY", "CKD", "ICE_GASOLINE", None, None,
                    None, "NOT_AT_IMPORT", False, False, None,
                    date(2020, 1, 1), None, _ICE_CKD_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "LOCAL_ASSEMBLY", "CKD", "ICE_DIESEL", None, None,
                    None, "NOT_AT_IMPORT", False, False, None,
                    date(2020, 1, 1), None, _ICE_CKD_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "LOCAL_ASSEMBLY", "CKD", "HEV", None, None,
                    None, "NOT_AT_IMPORT", False, False, None,
                    date(2020, 1, 1), None, _ICE_CKD_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "LOCAL_ASSEMBLY", "CKD", "PHEV", None, None,
                    None, "NOT_AT_IMPORT", False, False, None,
                    date(2020, 1, 1), None, _ICE_CKD_EXCISE_NOTE),
    DomesticTaxRule("MY", "EXCISE", "LOCAL_ASSEMBLY", "CKD", "EREV", None, None,
                    None, "NOT_AT_IMPORT", False, False, None,
                    date(2020, 1, 1), None, _ICE_CKD_EXCISE_NOTE),
    # ── CKD IMPORT SALES TAX (CONDITIONAL EXEMPTION) ──
    DomesticTaxRule("MY", "IMPORT_SALES_TAX", "AT_IMPORT", "CKD", None, None, None,
                    Decimal("0.10"), "CONDITIONAL_EXEMPTION", True, True,
                    "Royal Malaysian Customs (DG)",
                    date(2018, 9, 1), None, _CKD_IMPORT_SST_NOTE),
    # ── CKD FINISHED VEHICLE SST (LOCAL_ASSEMBLY) ──
    DomesticTaxRule("MY", "FINISHED_VEHICLE_SST", "LOCAL_ASSEMBLY", "CKD", None, None, None,
                    Decimal("0.10"), "STATUTORY_RATE", False, False, None,
                    date(2020, 1, 1), None, "本地组装成车销售税率（本地销售阶段，不受FTA影响）"),
]


# ── Resolver ────────────────────────────────────────────────────────


class DomesticTaxResolver:
    """Resolve Malaysian domestic tax rules for a given context.

    Currently uses seed data. Replace with DB queries when domestic_tax_rule
    table is populated with verified source data.
    """

    def __init__(self, _session: Any = None) -> None:
        # session param reserved for future DB-backed implementation
        self._rules = _SEED_RULES

    def resolve(
        self,
        *,
        country_iso2: str = "MY",
        effective_date: date | None = None,
        import_mode: str,
        powertrain: str = "",
        tax_code: TaxCode | None = None,
        stage: TaxStage | None = None,
    ) -> list[DomesticTaxRule]:
        """Return all matching domestic tax rules, filtered by context.

        If tax_code is provided, returns at most one rule per tax_code+stage.
        """
        results: list[DomesticTaxRule] = []

        for rule in self._rules:
            if rule.country_iso2 != country_iso2:
                continue
            if rule.import_mode != import_mode:
                continue
            if rule.powertrain is not None and powertrain and rule.powertrain != powertrain:
                continue
            if tax_code and rule.tax_code != tax_code:
                continue
            if stage and rule.stage != stage:
                continue
            if effective_date:
                if effective_date < rule.effective_from:
                    continue
                if rule.effective_to and effective_date > rule.effective_to:
                    continue
            results.append(replace(rule))

        return results

    def get_excise(self, *, import_mode: str, powertrain: str) -> DomesticTaxRule | None:
        rules = self.resolve(import_mode=import_mode, powertrain=powertrain, tax_code="EXCISE")
        return rules[0] if rules else None

    def get_sales_tax(self, *, import_mode: str, powertrain: str = "") -> DomesticTaxRule | None:
        rules = self.resolve(
            import_mode=import_mode, powertrain=powertrain, tax_code="SALES_TAX"
        )
        if not rules:
            # Fallback: generic SST rule (powertrain=None)
            rules = self.resolve(
                import_mode=import_mode, powertrain="",
                tax_code="SALES_TAX",
            )
        if not rules:
            # Try without powertrain filter
            rules = [r for r in self._rules if r.tax_code == "SALES_TAX" and r.import_mode == import_mode]
        return rules[0] if rules else None

    def get_import_sales_tax(self) -> DomesticTaxRule | None:
        rules = [
            r for r in self._rules
            if r.tax_code == "IMPORT_SALES_TAX" and r.import_mode == "CKD"
        ]
        return rules[0] if rules else None

    def get_finished_vehicle_sst(self, powertrain: str = "") -> DomesticTaxRule | None:
        rules = [
            r for r in self._rules
            if r.tax_code == "FINISHED_VEHICLE_SST"
            and r.import_mode == "CKD"
            and (r.powertrain is None or r.powertrain == powertrain)
        ]
        if not rules:
            rules = [
                r for r in self._rules
                if r.tax_code == "FINISHED_VEHICLE_SST" and r.import_mode == "CKD"
            ]
        return rules[0] if rules else None
