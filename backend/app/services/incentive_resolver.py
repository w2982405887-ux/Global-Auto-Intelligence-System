"""Malaysia automotive incentive resolver — DB-driven, no hardcoded policy dict.

Queries rules.automotive_incentive_program for active policies matching
date / powertrain / import_mode constraints.

Five-state lifecycle: POTENTIALLY_ELIGIBLE → REQUIRES_DOCUMENT → CONFIRMED
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

# ── Dataclasses ─────────────────────────────────────────────────────


Status = Literal[
    "POTENTIALLY_ELIGIBLE",  # Conditions match, awaiting user confirmation
    "REQUIRES_DOCUMENT",     # Conditions match but supporting docs needed
    "CONFIRMED",             # User confirmed eligibility + docs provided
    "NOT_ELIGIBLE",          # Conditions not met
    "EXPIRED",               # Policy has expired
]


@dataclass
class BenefitOverride:
    """Parsed benefit_expression JSONB from automotive_incentive_program."""
    benefit_type: str   # "TAX_OVERRIDE" | "PROJECT_APPROVAL" | "CUSTOM"
    target_taxes: list[str] = field(default_factory=list)
    overrides: dict[str, str] = field(default_factory=dict)
    requires_project_approval: bool = False
    note: str | None = None


@dataclass
class ResolvedPolicy:
    program_code: str
    program_name_cn: str
    status: Status
    status_chain: list[str] = field(default_factory=list)
    matched_conditions: list[str] = field(default_factory=list)
    required_documents: list[str] = field(default_factory=list)
    approval_authority: str | None = None
    incentive_scope: str | None = None
    condition_expression: dict[str, Any] | None = None
    benefit_expression: dict[str, Any] | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    benefit: BenefitOverride | None = None
    source_reference: dict[str, Any] = field(default_factory=dict)


@dataclass
class IncentiveValidationResult:
    resolved: list[ResolvedPolicy] = field(default_factory=list)
    invalid_codes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ResolvedTreatment:
    """A tax line after applying confirmed incentive policies."""
    tax_code: str
    stage: str
    statutory_rate: Decimal | None
    applied_rate: Decimal | None    # overridden by CONFIRMED policies only
    treatment: str
    is_conditional: bool
    approval_required: bool
    approval_confirmed: bool
    source_policy_code: str | None
    source_reference: dict[str, Any] = field(default_factory=dict)
    note: str = ""


# ── Resolver ────────────────────────────────────────────────────────


class IncentiveResolver:
    """DB-driven incentive matching. No hardcoded policy data."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def validate_selected_policies(
        self,
        selected_policy_codes: list[str],
        *,
        effective_date: date,
        powertrain: str,
        import_mode: str,  # "CBU" | "CKD"
    ) -> IncentiveValidationResult:
        """Validate user-selected policy codes against DB.

        Returns resolved policies with status + source references.
        """
        if not selected_policy_codes:
            return IncentiveValidationResult()

        rows = self._session.execute(
            text("""
                SELECT
                  program.program_code,
                  program.program_name_cn,
                  program.benefit_expression,
                  program.condition_expression,
                  program.incentive_scope,
                  program.powertrain,
                  program.import_mode,
                  program.approval_required,
                  program.approval_authority_id,
                  program.effective_from,
                  program.effective_to,
                  auth_approval.authority_name AS approval_authority_name,
                  doc.source_code AS source_id,
                  doc.document_title,
                  doc.document_number,
                  doc.source_type,
                  doc.canonical_url AS official_url,
                  doc_auth.authority_name AS doc_authority_name,
                  clause.locator_type,
                  clause.locator_value
                FROM rules.automotive_incentive_program program
                JOIN evidence.source_clause clause
                  ON clause.source_clause_id = program.source_clause_id
                JOIN evidence.source_document doc
                  ON doc.source_document_id = clause.source_document_id
                LEFT JOIN ref.authority doc_auth
                  ON doc_auth.authority_id = doc.authority_id
                LEFT JOIN ref.authority auth_approval
                  ON auth_approval.authority_id = program.approval_authority_id
                WHERE program.record_status = 'ACTIVE'
                  AND program.program_code = ANY(:codes)
            """),
            {"codes": selected_policy_codes},
        ).fetchall()

        found_codes = {row.program_code for row in rows}
        missing = [c for c in selected_policy_codes if c not in found_codes]

        result = IncentiveValidationResult(
            invalid_codes=missing,
            notes=[f"未知政策代码: {c}" for c in missing],
        )

        for row in rows:
            resolved = self._resolve_single_policy(
                row, effective_date, powertrain, import_mode,
            )
            result.resolved.append(resolved)

        return result

    def _resolve_single_policy(
        self,
        row: Any,
        effective_date: date,
        powertrain: str,
        import_mode: str,
    ) -> ResolvedPolicy:
        conditions: list[str] = []
        status_chain: list[str] = []
        docs_required: list[str] = []

        src = {
            "source_id": row.source_id or "",
            "document_title": row.document_title or "",
            "authority_name": row.doc_authority_name or "",
            "document_number": row.document_number,
            "source_type": row.source_type or "",
            "official_url": row.official_url,
            "locator": {
                "locator_type": row.locator_type or "",
                "locator_value": row.locator_value or "",
            },
        }
        common = {
            "source_reference": src,
            "incentive_scope": row.incentive_scope,
            "condition_expression": row.condition_expression,
            "benefit_expression": row.benefit_expression,
            "effective_from": row.effective_from,
            "effective_to": row.effective_to,
        }

        # Date check
        eff_from = row.effective_from
        eff_to = row.effective_to
        if effective_date < eff_from:
            return ResolvedPolicy(
                program_code=row.program_code,
                program_name_cn=row.program_name_cn,
                status="NOT_ELIGIBLE",
                status_chain=["NOT_ELIGIBLE"],
                matched_conditions=[f"生效日期 {eff_from}，当前日期 {effective_date} 尚未生效"],
                **common,
            )
        if eff_to and effective_date > eff_to:
            return ResolvedPolicy(
                program_code=row.program_code,
                program_name_cn=row.program_name_cn,
                status="EXPIRED",
                status_chain=["EXPIRED"],
                matched_conditions=[f"已于 {eff_to} 到期"],
                **common,
            )
        conditions.append(f"日期有效 ({eff_from} ~ {eff_to or '持续'})")
        status_chain.append("POTENTIALLY_ELIGIBLE")

        # Powertrain check
        if row.powertrain and row.powertrain != powertrain:
            return ResolvedPolicy(
                program_code=row.program_code,
                program_name_cn=row.program_name_cn,
                status="NOT_ELIGIBLE",
                status_chain=["NOT_ELIGIBLE"],
                matched_conditions=[
                    f"动力类型 {row.powertrain} 不匹配当前 {powertrain}",
                ],
                **common,
            )
        if row.powertrain:
            conditions.append(f"动力类型匹配 ({powertrain})")

        # Import mode check — "LOCAL_PRODUCTION" is a DB synonym for CKD
        db_mode = row.import_mode
        normalized_db_mode = "CKD" if db_mode == "LOCAL_PRODUCTION" else db_mode
        if db_mode and normalized_db_mode != import_mode:
            return ResolvedPolicy(
                program_code=row.program_code,
                program_name_cn=row.program_name_cn,
                status="NOT_ELIGIBLE",
                status_chain=["NOT_ELIGIBLE"],
                matched_conditions=[
                    f"进口模式 {db_mode} 不匹配当前 {import_mode}",
                ],
                **common,
            )
        if db_mode:
            conditions.append(f"进口模式匹配 ({import_mode})")

        # Approval required?
        if row.approval_required:
            docs_required.append(
                f"{row.approval_authority_name or '主管机关'} 批准"
            )
            status_chain.append("REQUIRES_DOCUMENT")

        # Parse benefit
        benefit = _parse_benefit_expression(row.benefit_expression or {})

        final_status: Status = (
            "REQUIRES_DOCUMENT" if docs_required
            else "POTENTIALLY_ELIGIBLE"
        )

        return ResolvedPolicy(
            program_code=row.program_code,
            program_name_cn=row.program_name_cn,
            status=final_status,
            status_chain=status_chain,
            matched_conditions=conditions,
            required_documents=docs_required,
            approval_authority=row.approval_authority_name,
            benefit=benefit,
            **common,
        )

    @staticmethod
    def resolve_applied_treatment(
        tax_code: str,
        stage: str,
        statutory_rate: Decimal | None,
        treatment: str,
        *,
        import_mode: str,
        powertrain: str,
        effective_date: date,
        resolved_policies: list[ResolvedPolicy],
        is_ckd: bool = False,
    ) -> ResolvedTreatment:
        """Resolve applied (post-incentive) rate from confirmed policies.

        Only CONFIRMED policies override the rate.
        POTENTIALLY_ELIGIBLE / REQUIRES_DOCUMENT → statutory rate applies (with warning).
        """
        matched_policy: ResolvedPolicy | None = None

        for rp in resolved_policies:
            if rp.status not in ("CONFIRMED",):
                continue
            if rp.benefit is None:
                continue
            if tax_code in rp.benefit.target_taxes:
                matched_policy = rp
                break

        if matched_policy and matched_policy.benefit:
            ov = matched_policy.benefit.overrides
            key_map = {
                "EXCISE": "excise_rate",
                "SALES_TAX": "sales_tax_rate",
                "IMPORT_SALES_TAX": "sales_tax_rate",
                "FINISHED_VEHICLE_SST": "sales_tax_rate",
                "IMPORT_DUTY": "import_duty_rate",
            }
            override_key = key_map.get(tax_code)
            if override_key and override_key in ov:
                applied = (
                    Decimal(ov[override_key])
                    if ov[override_key] is not None
                    else None
                )
                return ResolvedTreatment(
                    tax_code=tax_code,
                    stage=stage,
                    statutory_rate=statutory_rate,
                    applied_rate=applied,
                    treatment=(
                        "CONDITIONAL_EXEMPTION"
                        if matched_policy.benefit.benefit_type == "TAX_OVERRIDE"
                        else treatment
                    ),
                    is_conditional=matched_policy.benefit.benefit_type != "TAX_OVERRIDE",
                    approval_required=False,
                    approval_confirmed=True,
                    source_policy_code=matched_policy.program_code,
                    source_reference=matched_policy.source_reference,
                    note=f"{matched_policy.program_name_cn}（已确认）",
                )

            # PROJECT_APPROVAL type — rate comes from approval letter
            if matched_policy.benefit.requires_project_approval:
                return ResolvedTreatment(
                    tax_code=tax_code,
                    stage=stage,
                    statutory_rate=statutory_rate,
                    applied_rate=statutory_rate,  # keep statutory until approval confirmed
                    treatment="CONDITIONAL_EXEMPTION",
                    is_conditional=True,
                    approval_required=True,
                    approval_confirmed=False,
                    source_policy_code=matched_policy.program_code,
                    source_reference=matched_policy.source_reference,
                    note=f"{matched_policy.program_name_cn}（需批准书决定最终税率）",
                )

        # No CONFIRMED policy matched — check if any POTENTIALLY_ELIGIBLE exists
        pending = [
            rp for rp in resolved_policies
            if rp.status in ("POTENTIALLY_ELIGIBLE", "REQUIRES_DOCUMENT")
            and rp.benefit
            and tax_code in rp.benefit.target_taxes
        ]
        if pending:
            p = pending[0]
            return ResolvedTreatment(
                tax_code=tax_code,
                stage=stage,
                statutory_rate=statutory_rate,
                applied_rate=statutory_rate,
                treatment=(
                    "CONDITIONAL_EXEMPTION"
                    if p.benefit and p.benefit.benefit_type == "TAX_OVERRIDE"
                    else treatment
                ),
                is_conditional=True,
                approval_required=p.status == "REQUIRES_DOCUMENT",
                approval_confirmed=False,
                source_policy_code=p.program_code,
                source_reference=p.source_reference,
                note=f"{p.program_name_cn}（状态: {p.status}，需用户确认后生效）",
            )

        # Default: statutory treatment
        return ResolvedTreatment(
            tax_code=tax_code,
            stage=stage,
            statutory_rate=statutory_rate,
            applied_rate=(
                statutory_rate
                if treatment not in ("EXEMPT", "NOT_AT_IMPORT", "CONDITIONAL_EXEMPTION")
                else None
            ),
            treatment=treatment,
            is_conditional=(treatment in ("EXEMPT", "CONDITIONAL_EXEMPTION")),
            approval_required=False,
            approval_confirmed=False,
            source_policy_code=None,
            note=f"法定税率，未匹配已确认的优惠政策（{treatment}）",
        )


# ── Benefit parser ──────────────────────────────────────────────────


def _parse_benefit_expression(expr: dict[str, Any]) -> BenefitOverride | None:
    """Convert DB benefit_expression JSONB to structured BenefitOverride."""
    if not expr:
        return None

    # Check for TAX_OVERRIDE pattern (e.g. BEV full exemption)
    rate_overrides = {}
    target_taxes: list[str] = []

    mapping = {
        "component_import_duty_rate_override": ("IMPORT_DUTY", "import_duty_rate"),
        "finished_vehicle_excise_rate_override": ("EXCISE", "excise_rate"),
        "finished_vehicle_sales_tax_rate_override": ("FINISHED_VEHICLE_SST", "sales_tax_rate"),
    }
    for db_key, (tax_code, override_key) in mapping.items():
        if db_key in expr:
            target_taxes.append(tax_code)
            rate_overrides[override_key] = str(expr[db_key])

    # Check for PROJECT_APPROVAL pattern
    rate_source = expr.get("rate_source", "")
    if rate_source == "ENTERPRISE_PROJECT_APPROVAL":
        target_taxes = list(target_taxes) if target_taxes else ["EXCISE", "SALES_TAX"]
        return BenefitOverride(
            benefit_type="PROJECT_APPROVAL",
            target_taxes=target_taxes,
            overrides={},
            requires_project_approval=True,
            note="无公开默认税率，具体激励由批准书决定",
        )

    # Check for explicit approval requirement
    if expr.get("benefit_applies_only_with_approval"):
        return BenefitOverride(
            benefit_type="TAX_OVERRIDE",
            target_taxes=target_taxes,
            overrides=rate_overrides,
            requires_project_approval=True,
            note="需批准后适用，本系统展示条件性豁免情景",
        )

    if rate_overrides:
        return BenefitOverride(
            benefit_type="TAX_OVERRIDE",
            target_taxes=target_taxes,
            overrides=rate_overrides,
            requires_project_approval=False,
            note=None,
        )

    return BenefitOverride(
        benefit_type="CUSTOM",
        target_taxes=target_taxes,
        overrides=rate_overrides,
        requires_project_approval=False,
        note=str(expr),
    )
