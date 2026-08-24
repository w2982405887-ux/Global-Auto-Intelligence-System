from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.calculation_engine import (
    CalculationEngine,
    ComparisonRequest,
    ItemCostInput,
    PreferenceEligibility,
    ProfitInput,
)
from app.services.decision_repository import DecisionRepository
from app.services.tariff_repository import TariffRepository


class ProjectBomService:
    """Project-level BOM/CCU allocation and deterministic regime comparison."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._projects = DecisionRepository(session)

    def list_lines(self, project_id: UUID | str) -> dict[str, Any]:
        project = self._projects.get_project(project_id)
        rows = self._session.execute(
            text(
                """
                SELECT
                  line.project_bom_line_id, line.line_no,
                  line.enterprise_part_no, line.part_name,
                  ccu.ccu_code, ccu.ccu_name_cn, ccu.vehicle_system,
                  bucket.bucket_code, bucket.bucket_name_cn,
                  line.customs_value, line.quantity, line.currency_code,
                  origin.iso2 AS origin_country_iso2,
                  line.local_or_imported, line.enterprise_inputs_complete,
                  line.gri_2a_review_complete, line.notes,
                  line.record_status::text AS record_status,
                  COALESCE(
                    jsonb_object_agg(
                      selection.regime,
                      jsonb_build_object(
                        'tariff_mapping_id', mapping.mapping_id,
                        'mapping_code', mapping.mapping_code,
                        'national_tariff_code', mapping.national_tariff_code,
                        'duty_rate', mapping.duty_rate,
                        'verification_status', mapping.verification_status::text
                      )
                    ) FILTER (WHERE selection.regime IS NOT NULL),
                    '{}'::jsonb
                  ) AS selections
                FROM enterprise.project_bom_line line
                JOIN customs.customs_classification_unit ccu
                  ON ccu.ccu_id = line.ccu_id
                LEFT JOIN rules.kd_tax_bucket_definition bucket
                  ON bucket.kd_tax_bucket_id = line.kd_tax_bucket_id
                LEFT JOIN ref.country origin
                  ON origin.country_id = line.origin_country_id
                LEFT JOIN enterprise.project_bom_tariff_selection selection
                  ON selection.project_bom_line_id = line.project_bom_line_id
                LEFT JOIN customs.tariff_mapping mapping
                  ON mapping.mapping_id = selection.tariff_mapping_id
                WHERE line.project_id = :project_id
                GROUP BY
                  line.project_bom_line_id, ccu.ccu_code, ccu.ccu_name_cn,
                  ccu.vehicle_system, bucket.bucket_code, bucket.bucket_name_cn,
                  origin.iso2
                ORDER BY line.line_no
                """
            ),
            {"project_id": str(project_id)},
        ).mappings()
        items = [dict(row) for row in rows]
        imported_value = sum(
            (Decimal(str(row["customs_value"])) for row in items
             if row["local_or_imported"] == "IMPORTED"),
            Decimal("0"),
        )
        return {
            "project_id": str(project["project_id"]),
            "project_code": project["project_code"],
            "currency_code": "MYR",
            "items": items,
            "summary": {
                "line_count": len(items),
                "imported_line_count": sum(
                    1 for row in items if row["local_or_imported"] == "IMPORTED"
                ),
                "local_line_count": sum(
                    1 for row in items if row["local_or_imported"] == "LOCAL"
                ),
                "imported_customs_value": imported_value,
            },
        }

    def upsert_line(
        self, project_id: UUID | str, line_no: int, payload: Any
    ) -> str:
        project = self._projects.get_project(project_id)
        ccu_id = self._session.execute(
            text(
                """
                SELECT ccu_id
                FROM customs.customs_classification_unit
                WHERE ccu_code = :ccu_code AND record_status = 'ACTIVE'
                ORDER BY version DESC LIMIT 1
                """
            ),
            {"ccu_code": payload.ccu_code},
        ).scalar_one_or_none()
        if ccu_id is None:
            raise ValueError(f"CCU {payload.ccu_code} not found")
        bucket_id = None
        if payload.bucket_code:
            bucket_id = self._session.execute(
                text(
                    """
                    SELECT kd_tax_bucket_id
                    FROM rules.kd_tax_bucket_definition
                    WHERE bucket_code = :bucket_code
                      AND record_status = 'ACTIVE'
                    ORDER BY version DESC LIMIT 1
                    """
                ),
                {"bucket_code": payload.bucket_code},
            ).scalar_one_or_none()
            if bucket_id is None:
                raise ValueError(f"KD bucket {payload.bucket_code} not found")
        origin_id = self._session.execute(
            text("SELECT country_id FROM ref.country WHERE iso2 = :iso2"),
            {"iso2": payload.origin_country_iso2.upper()},
        ).scalar_one_or_none()
        if origin_id is None:
            raise ValueError(f"Origin {payload.origin_country_iso2} not found")
        line_id = self._session.execute(
            text(
                """
                INSERT INTO enterprise.project_bom_line (
                  project_id, line_no, enterprise_part_no, part_name,
                  ccu_id, kd_tax_bucket_id, customs_value, quantity,
                  currency_code, origin_country_id, local_or_imported,
                  enterprise_inputs_complete, gri_2a_review_complete,
                  notes, record_status
                ) VALUES (
                  :project_id, :line_no, :part_no, :part_name,
                  :ccu_id, :bucket_id, :customs_value, :quantity,
                  :currency_code, :origin_id, :local_or_imported,
                  :inputs_complete, :gri_complete, :notes, 'ACTIVE'
                )
                ON CONFLICT (project_id, line_no)
                DO UPDATE SET
                  enterprise_part_no = EXCLUDED.enterprise_part_no,
                  part_name = EXCLUDED.part_name,
                  ccu_id = EXCLUDED.ccu_id,
                  kd_tax_bucket_id = EXCLUDED.kd_tax_bucket_id,
                  customs_value = EXCLUDED.customs_value,
                  quantity = EXCLUDED.quantity,
                  currency_code = EXCLUDED.currency_code,
                  origin_country_id = EXCLUDED.origin_country_id,
                  local_or_imported = EXCLUDED.local_or_imported,
                  enterprise_inputs_complete = EXCLUDED.enterprise_inputs_complete,
                  gri_2a_review_complete = EXCLUDED.gri_2a_review_complete,
                  notes = EXCLUDED.notes,
                  record_status = 'ACTIVE',
                  updated_at = now()
                RETURNING project_bom_line_id
                """
            ),
            {
                "project_id": str(project["project_id"]),
                "line_no": line_no,
                "part_no": payload.enterprise_part_no,
                "part_name": payload.part_name,
                "ccu_id": ccu_id,
                "bucket_id": bucket_id,
                "customs_value": payload.customs_value,
                "quantity": payload.quantity,
                "currency_code": payload.currency_code,
                "origin_id": origin_id,
                "local_or_imported": payload.local_or_imported,
                "inputs_complete": payload.enterprise_inputs_complete,
                "gri_complete": payload.gri_2a_review_complete,
                "notes": payload.notes,
            },
        ).scalar_one()
        return str(line_id)

    def delete_line(self, project_id: UUID | str, line_no: int) -> None:
        result = self._session.execute(
            text(
                """
                DELETE FROM enterprise.project_bom_line
                WHERE project_id = :project_id AND line_no = :line_no
                """
            ),
            {"project_id": str(project_id), "line_no": line_no},
        )
        if result.rowcount != 1:
            raise ValueError(f"BOM line {line_no} not found")

    def select_mapping(
        self,
        project_id: UUID | str,
        line_no: int,
        regime: str,
        mapping_code: str,
        selected_by: str,
        selection_note: str | None,
    ) -> str:
        row = self._session.execute(
            text(
                """
                SELECT line.project_bom_line_id, ccu.ccu_id
                FROM enterprise.project_bom_line line
                JOIN customs.customs_classification_unit ccu
                  ON ccu.ccu_id = line.ccu_id
                WHERE line.project_id = :project_id AND line.line_no = :line_no
                """
            ),
            {"project_id": str(project_id), "line_no": line_no},
        ).mappings().one_or_none()
        if row is None:
            raise ValueError(f"BOM line {line_no} not found")
        mapping = self._session.execute(
            text(
                """
                SELECT mapping.mapping_id,
                       COALESCE(agreement.agreement_code, 'MFN') AS regime
                FROM customs.tariff_mapping mapping
                JOIN customs.ccu_candidate_hs candidate
                  ON candidate.candidate_id = mapping.candidate_id
                LEFT JOIN ref.trade_agreement agreement
                  ON agreement.trade_agreement_id = mapping.trade_agreement_id
                WHERE mapping.mapping_code = :mapping_code
                  AND candidate.ccu_id = :ccu_id
                  AND mapping.record_status = 'ACTIVE'
                """
            ),
            {"mapping_code": mapping_code, "ccu_id": row["ccu_id"]},
        ).mappings().one_or_none()
        if mapping is None or mapping["regime"] != regime:
            raise ValueError(
                f"Mapping {mapping_code} is not an active {regime} option for this CCU"
            )
        selection_id = self._session.execute(
            text(
                """
                INSERT INTO enterprise.project_bom_tariff_selection (
                  project_bom_line_id, regime, tariff_mapping_id,
                  selected_by, selection_note
                ) VALUES (
                  :line_id, :regime, :mapping_id, :selected_by, :selection_note
                )
                ON CONFLICT (project_bom_line_id, regime)
                DO UPDATE SET
                  tariff_mapping_id = EXCLUDED.tariff_mapping_id,
                  selected_by = EXCLUDED.selected_by,
                  selection_note = EXCLUDED.selection_note,
                  updated_at = now()
                RETURNING project_bom_tariff_selection_id
                """
            ),
            {
                "line_id": row["project_bom_line_id"],
                "regime": regime,
                "mapping_id": mapping["mapping_id"],
                "selected_by": selected_by,
                "selection_note": selection_note,
            },
        ).scalar_one()
        return str(selection_id)

    def preview(
        self,
        project_id: UUID | str,
        *,
        requested_regimes: tuple[str, ...],
        eligibility: dict[str, Any],
        sales_revenue: Decimal | None,
        non_import_costs: Decimal | None,
        recoverable_sst_fraction: Decimal,
    ) -> Any:
        result, _ = self.build_comparison(
            project_id,
            requested_regimes=requested_regimes,
            eligibility=eligibility,
            sales_revenue=sales_revenue,
            non_import_costs=non_import_costs,
            recoverable_sst_fraction=recoverable_sst_fraction,
        )
        return result

    def build_comparison(
        self,
        project_id: UUID | str,
        *,
        requested_regimes: tuple[str, ...],
        eligibility: dict[str, Any],
        sales_revenue: Decimal | None,
        non_import_costs: Decimal | None,
        recoverable_sst_fraction: Decimal,
    ) -> tuple[Any, dict[str, Any]]:
        project = self._projects.get_project(project_id)
        bom = self.list_lines(project_id)
        imported = [
            item for item in bom["items"] if item["local_or_imported"] == "IMPORTED"
        ]
        if not imported:
            raise ValueError("At least one imported BOM/CCU line is required")
        ccu_codes = tuple(item["ccu_code"] for item in imported)
        options = TariffRepository(self._session).list_effective_options(
            country_iso2="MY",
            ccu_codes=ccu_codes,
            as_of=project["calculation_date"],
        )
        selections = {
            item["ccu_code"]: {
                regime: selected["mapping_code"]
                for regime, selected in item["selections"].items()
            }
            for item in imported
        }
        selected = TariffRepository.require_explicit_selection(options, selections)
        request = ComparisonRequest(
            country_iso2="MY",
            import_date=project["calculation_date"],
            currency_code="MYR",
            items=tuple(
                ItemCostInput(
                    ccu_code=item["ccu_code"],
                    customs_value=Decimal(str(item["customs_value"])),
                    selected_rates=selected[item["ccu_code"]],
                    enterprise_inputs_complete=item["enterprise_inputs_complete"],
                    gri_2a_review_complete=item["gri_2a_review_complete"],
                )
                for item in imported
            ),
            requested_regimes=requested_regimes,
            baseline_regime="MFN",
            allow_mfn_fallback=True,
            eligibility={
                regime: PreferenceEligibility(regime=regime, **values)
                for regime, values in eligibility.items()
            },
            profit=ProfitInput(
                sales_revenue=sales_revenue,
                non_import_costs=non_import_costs,
                recoverable_sst_fraction=recoverable_sst_fraction,
            ),
        )
        result = CalculationEngine().compare(request)
        request_payload = {
            "project_id": str(project["project_id"]),
            "project_code": project["project_code"],
            "country_iso2": "MY",
            "import_date": project["calculation_date"],
            "currency_code": "MYR",
            "route_code": project["selected_route_code"],
            "items": [
                {
                    "line_no": item["line_no"],
                    "enterprise_part_no": item["enterprise_part_no"],
                    "ccu_code": item["ccu_code"],
                    "customs_value": item["customs_value"],
                    "quantity": item["quantity"],
                    "origin_country_iso2": item["origin_country_iso2"],
                    "selected_rates": selections[item["ccu_code"]],
                    "enterprise_inputs_complete": item["enterprise_inputs_complete"],
                    "gri_2a_review_complete": item["gri_2a_review_complete"],
                }
                for item in imported
            ],
            "requested_regimes": list(requested_regimes),
            "baseline_regime": "MFN",
            "allow_mfn_fallback": True,
            "eligibility": eligibility,
            "profit": {
                "sales_revenue": sales_revenue,
                "non_import_costs": non_import_costs,
                "recoverable_sst_fraction": recoverable_sst_fraction,
            },
        }
        return result, request_payload
