from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def _read_path(payload: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return False, None
        current = current[segment]
    return True, current


def _condition_matches(condition: dict[str, Any], facts: dict[str, Any]) -> bool:
    if "all" in condition:
        return all(_condition_matches(item, facts) for item in condition["all"])
    if "any" in condition:
        return any(_condition_matches(item, facts) for item in condition["any"])
    if "not" in condition:
        return not _condition_matches(condition["not"], facts)

    field = condition.get("field")
    operator = condition.get("operator")
    expected = condition.get("value")
    if not isinstance(field, str):
        return False
    exists, actual = _read_path(facts, field)
    if operator == "EXISTS":
        return exists is bool(expected)
    if not exists:
        return False
    if operator == "EQ":
        return actual == expected
    if operator == "NE":
        return actual != expected
    if operator == "IN":
        return actual in expected
    if operator == "NOT_IN":
        return actual not in expected
    return False


class DecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def resolve_route(
        routes: list[dict[str, Any]], facts: dict[str, Any]
    ) -> dict[str, Any]:
        matches = [
            route
            for route in routes
            if _condition_matches(route["decision_condition"], facts)
        ]
        selected = matches[0] if len(matches) == 1 else None
        return {
            "selected_route_code": selected["route_code"] if selected else None,
            "verification_status": (
                selected["verification_status"] if selected else "UNVERIFIED"
            ),
            "required_input_fields": (
                selected["required_input_fields"] if selected else []
            ),
            "fallback_route_code": (
                selected["fallback_route_code"] if selected else None
            ),
            "matched_route_codes": [route["route_code"] for route in matches],
            "resolution_status": (
                "RESOLVED"
                if len(matches) == 1
                else "NO_MATCH"
                if not matches
                else "AMBIGUOUS"
            ),
        }

    def create_project(self, payload: Any) -> dict[str, Any]:
        country_id = self._session.execute(
            text(
                """
                SELECT country_id
                FROM ref.country
                WHERE iso2 = :iso2 AND record_status = 'ACTIVE'
                """
            ),
            {"iso2": payload.country_iso2.upper()},
        ).scalar_one_or_none()
        if country_id is None:
            raise ValueError(f"Country {payload.country_iso2.upper()} not found")

        existing_project = self._session.execute(
            text(
                """
                SELECT project_id, enterprise_code
                FROM enterprise.decision_project
                WHERE project_code = :project_code
                """
            ),
            {"project_code": payload.project_code},
        ).mappings().one_or_none()
        if existing_project is not None:
            if existing_project["enterprise_code"] != payload.enterprise_code:
                raise ValueError(
                    f"Project code {payload.project_code} belongs to another enterprise"
                )
            return self.get_project(existing_project["project_id"])

        vehicle_id = self._session.execute(
            text(
                """
                INSERT INTO enterprise.vehicle_model (
                  model_code,
                  vehicle_type,
                  powertrain,
                  technical_attributes,
                  effective_from,
                  version,
                  record_status
                )
                VALUES (
                  :model_code,
                  :vehicle_type,
                  CAST(:powertrain AS ref.powertrain),
                  CAST(:technical_attributes AS jsonb),
                  :calculation_date,
                  1,
                  'ACTIVE'
                )
                ON CONFLICT (model_code, version)
                DO UPDATE SET
                  vehicle_type = EXCLUDED.vehicle_type,
                  powertrain = EXCLUDED.powertrain,
                  technical_attributes = EXCLUDED.technical_attributes,
                  record_status = 'ACTIVE'
                RETURNING vehicle_id
                """
            ),
            {
                "model_code": payload.model_code,
                "vehicle_type": payload.vehicle_type,
                "powertrain": payload.powertrain,
                "technical_attributes": json.dumps(
                    payload.technical_attributes, ensure_ascii=False
                ),
                "calculation_date": payload.calculation_date,
            },
        ).scalar_one()
        project_id = self._session.execute(
            text(
                """
                INSERT INTO enterprise.decision_project (
                  project_code,
                  enterprise_code,
                  project_name,
                  country_id,
                  vehicle_id,
                  calculation_date,
                  project_payload
                )
                VALUES (
                  :project_code,
                  :enterprise_code,
                  :project_name,
                  :country_id,
                  :vehicle_id,
                  :calculation_date,
                  CAST(:project_payload AS jsonb)
                )
                RETURNING project_id
                """
            ),
            {
                "project_code": payload.project_code,
                "enterprise_code": payload.enterprise_code,
                "project_name": payload.project_name,
                "country_id": country_id,
                "vehicle_id": vehicle_id,
                "calculation_date": payload.calculation_date,
                "project_payload": json.dumps(
                    {
                        "model_code": payload.model_code,
                        "vehicle_type": payload.vehicle_type,
                        "powertrain": payload.powertrain,
                    },
                    ensure_ascii=False,
                ),
            },
        ).scalar_one()
        return self.get_project(project_id)

    def get_project(self, project_id: UUID | str) -> dict[str, Any]:
        row = self._session.execute(
            text(
                """
                SELECT
                  project.project_id,
                  project.project_code,
                  project.enterprise_code,
                  project.project_name,
                  country.iso2 AS country_iso2,
                  country.country_name_cn,
                  project.calculation_date,
                  project.selected_route_code,
                  project.route_facts,
                  project.project_payload,
                  project.verification_status::text AS verification_status,
                  project.record_status::text AS record_status,
                  project.created_at,
                  project.updated_at,
                  vehicle.vehicle_id,
                  vehicle.model_code,
                  vehicle.vehicle_type,
                  vehicle.powertrain::text AS powertrain,
                  vehicle.technical_attributes
                FROM enterprise.decision_project project
                JOIN ref.country country ON country.country_id = project.country_id
                LEFT JOIN enterprise.vehicle_model vehicle
                  ON vehicle.vehicle_id = project.vehicle_id
                WHERE project.project_id = :project_id
                """
            ),
            {"project_id": str(project_id)},
        ).mappings().one_or_none()
        if row is None:
            raise ValueError(f"Project {project_id} not found")
        return dict(row)

    def save_route_resolution(
        self,
        *,
        project_id: UUID | str,
        facts: dict[str, Any],
        selected_route_code: str | None,
    ) -> dict[str, Any]:
        self._session.execute(
            text(
                """
                UPDATE enterprise.decision_project
                SET
                  route_facts = CAST(:facts AS jsonb),
                  selected_route_code = CAST(:selected_route_code AS text),
                  verification_status = CAST(CASE
                    WHEN CAST(:selected_route_code AS text) IS NULL THEN 'UNVERIFIED'
                    ELSE 'CANDIDATE'
                  END AS ref.verification_status),
                  updated_at = now()
                WHERE project_id = :project_id
                """
            ),
            {
                "project_id": str(project_id),
                "facts": json.dumps(facts, ensure_ascii=False),
                "selected_route_code": selected_route_code,
            },
        )
        return self.get_project(project_id)

    def project_inputs(self, project_id: UUID | str) -> list[dict[str, Any]]:
        rows = self._session.execute(
            text(
                """
                SELECT
                  required.field_path,
                  value.value_payload,
                  COALESCE(value.value_status::text, 'EMPTY') AS value_status,
                  COALESCE(value.evidence_refs, '[]'::jsonb) AS evidence_refs,
                  value.notes,
                  value.provided_by,
                  value.provided_at,
                  value.verified_by,
                  value.verified_at
                FROM enterprise.decision_project project
                JOIN rules.vehicle_tax_route route
                  ON route.route_code = project.selected_route_code
                 AND route.country_id = project.country_id
                 AND route.record_status = 'ACTIVE'
                 AND route.effective_from <= project.calculation_date
                 AND (
                   route.effective_to IS NULL
                   OR route.effective_to > project.calculation_date
                 )
                CROSS JOIN LATERAL jsonb_array_elements_text(
                  route.required_input_fields
                ) required(field_path)
                LEFT JOIN enterprise.project_input_value value
                  ON value.project_id = project.project_id
                 AND value.field_path = required.field_path
                WHERE project.project_id = :project_id
                ORDER BY required.field_path
                """
            ),
            {"project_id": str(project_id)},
        ).mappings()
        return [dict(row) for row in rows]

    def set_project_input(
        self,
        *,
        project_id: UUID | str,
        field_path: str,
        value_payload: Any,
        provided_by: str,
        evidence_refs: list[str],
        notes: str | None,
    ) -> str:
        input_id = self._session.execute(
            text(
                """
                INSERT INTO enterprise.project_input_value (
                  project_id,
                  field_path,
                  value_payload,
                  value_status,
                  evidence_refs,
                  notes,
                  provided_by,
                  provided_at
                )
                VALUES (
                  :project_id,
                  :field_path,
                  CAST(:value_payload AS jsonb),
                  'PROVIDED',
                  CAST(:evidence_refs AS jsonb),
                  :notes,
                  :provided_by,
                  now()
                )
                ON CONFLICT (project_id, field_path)
                DO UPDATE SET
                  value_payload = EXCLUDED.value_payload,
                  value_status = 'PROVIDED',
                  evidence_refs = EXCLUDED.evidence_refs,
                  notes = EXCLUDED.notes,
                  provided_by = EXCLUDED.provided_by,
                  provided_at = now(),
                  verified_by = NULL,
                  verified_at = NULL,
                  updated_at = now()
                RETURNING project_input_value_id
                """
            ),
            {
                "project_id": str(project_id),
                "field_path": field_path,
                "value_payload": json.dumps(value_payload, ensure_ascii=False),
                "evidence_refs": json.dumps(evidence_refs, ensure_ascii=False),
                "notes": notes,
                "provided_by": provided_by,
            },
        ).scalar_one()
        return str(input_id)

    def clear_project_input(
        self, *, project_id: UUID | str, field_path: str
    ) -> None:
        self._session.execute(
            text(
                """
                DELETE FROM enterprise.project_input_value
                WHERE project_id = :project_id AND field_path = :field_path
                """
            ),
            {"project_id": str(project_id), "field_path": field_path},
        )

    def completion(self, project_id: UUID | str) -> dict[str, Any]:
        row = self._session.execute(
            text(
                """
                SELECT *
                FROM enterprise.v_project_input_completion
                WHERE project_id = :project_id
                """
            ),
            {"project_id": str(project_id)},
        ).mappings().one_or_none()
        if row is None:
            project = self.get_project(project_id)
            return {
                "project_id": project["project_id"],
                "project_code": project["project_code"],
                "selected_route_code": project["selected_route_code"],
                "required_count": 0,
                "accepted_required_count": 0,
                "missing_required_count": 0,
                "completion_ratio": Decimal("0"),
                "ready_for_preview": False,
            }
        return dict(row)

    def requirements(self, project_id: UUID | str) -> list[dict[str, Any]]:
        rows = self._session.execute(
            text(
                """
                SELECT
                  requirement.requirement_code,
                  requirement.requirement_type::text AS requirement_type,
                  requirement.applicable_object,
                  requirement.import_mode::text AS import_mode,
                  requirement.powertrain::text AS powertrain,
                  requirement.trigger_condition,
                  requirement.required_document,
                  requirement.failure_consequence,
                  requirement.verification_status::text AS verification_status,
                  authority.authority_name,
                  source.source_code,
                  source.canonical_url,
                  clause.locator_value AS source_locator,
                  approval.project_approval_id,
                  approval.approval_reference,
                  approval.approval_status,
                  approval.issue_date,
                  approval.effective_from AS approval_effective_from,
                  approval.effective_to AS approval_effective_to,
                  approval.covered_model,
                  approval.covered_tariff_codes,
                  approval.approved_rate,
                  approval.exemption_scope,
                  approval.evidence_ref,
                  approval.notes,
                  approval.verification_status::text AS approval_verification_status
                FROM enterprise.decision_project project
                JOIN rules.vehicle_tax_route route
                  ON route.route_code = project.selected_route_code
                 AND route.country_id = project.country_id
                LEFT JOIN enterprise.vehicle_model vehicle
                  ON vehicle.vehicle_id = project.vehicle_id
                JOIN rules.approval_matrix requirement
                  ON requirement.country_id = project.country_id
                 AND requirement.record_status = 'ACTIVE'
                 AND requirement.effective_from <= project.calculation_date
                 AND (
                   requirement.effective_to IS NULL
                   OR requirement.effective_to > project.calculation_date
                 )
                 AND (
                   requirement.import_mode IS NULL
                   OR requirement.import_mode = route.import_mode
                   OR (
                     route.route_kind <> 'CBU'
                     AND requirement.import_mode::text = 'LOCAL_PRODUCTION'
                   )
                 )
                 AND (
                   requirement.powertrain IS NULL
                   OR requirement.powertrain = vehicle.powertrain
                 )
                LEFT JOIN ref.authority authority
                  ON authority.authority_id = requirement.authority_id
                JOIN evidence.source_clause clause
                  ON clause.source_clause_id = requirement.source_clause_id
                JOIN evidence.source_document source
                  ON source.source_document_id = clause.source_document_id
                LEFT JOIN enterprise.project_approval approval
                  ON approval.project_id = project.project_id
                 AND approval.requirement_id = requirement.requirement_id
                WHERE project.project_id = :project_id
                ORDER BY
                  CASE requirement.requirement_type::text
                    WHEN 'MANDATORY' THEN 1
                    ELSE 2
                  END,
                  requirement.requirement_code
                """
            ),
            {"project_id": str(project_id)},
        ).mappings()
        return [dict(row) for row in rows]

    def upsert_approval(
        self, *, project_id: UUID | str, requirement_code: str, payload: Any
    ) -> str:
        requirement_id = self._session.execute(
            text(
                """
                SELECT requirement.requirement_id
                FROM rules.approval_matrix requirement
                JOIN enterprise.decision_project project
                  ON project.country_id = requirement.country_id
                WHERE project.project_id = :project_id
                  AND requirement.requirement_code = :requirement_code
                  AND requirement.record_status = 'ACTIVE'
                """
            ),
            {
                "project_id": str(project_id),
                "requirement_code": requirement_code,
            },
        ).scalar_one_or_none()
        if requirement_id is None:
            raise ValueError(f"Requirement {requirement_code} not found")
        approval_id = self._session.execute(
            text(
                """
                INSERT INTO enterprise.project_approval (
                  project_id,
                  requirement_id,
                  approval_reference,
                  approval_status,
                  authority_name,
                  issue_date,
                  effective_from,
                  effective_to,
                  covered_model,
                  covered_tariff_codes,
                  approved_rate,
                  exemption_scope,
                  evidence_ref,
                  notes,
                  verification_status
                )
                VALUES (
                  :project_id,
                  :requirement_id,
                  :approval_reference,
                  :approval_status,
                  :authority_name,
                  :issue_date,
                  :effective_from,
                  :effective_to,
                  :covered_model,
                  CAST(:covered_tariff_codes AS jsonb),
                  :approved_rate,
                  CAST(:exemption_scope AS jsonb),
                  :evidence_ref,
                  :notes,
                  CAST(CASE
                    WHEN :approval_status = 'VERIFIED' THEN 'VERIFIED'
                    WHEN :approval_status = 'PROVIDED' THEN 'CANDIDATE'
                    ELSE 'UNVERIFIED'
                  END AS ref.verification_status)
                )
                ON CONFLICT (project_id, requirement_id)
                DO UPDATE SET
                  approval_reference = EXCLUDED.approval_reference,
                  approval_status = EXCLUDED.approval_status,
                  authority_name = EXCLUDED.authority_name,
                  issue_date = EXCLUDED.issue_date,
                  effective_from = EXCLUDED.effective_from,
                  effective_to = EXCLUDED.effective_to,
                  covered_model = EXCLUDED.covered_model,
                  covered_tariff_codes = EXCLUDED.covered_tariff_codes,
                  approved_rate = EXCLUDED.approved_rate,
                  exemption_scope = EXCLUDED.exemption_scope,
                  evidence_ref = EXCLUDED.evidence_ref,
                  notes = EXCLUDED.notes,
                  verification_status = EXCLUDED.verification_status,
                  updated_at = now()
                RETURNING project_approval_id
                """
            ),
            {
                "project_id": str(project_id),
                "requirement_id": requirement_id,
                **payload.model_dump(
                    mode="json",
                    exclude={"covered_tariff_codes", "exemption_scope"},
                ),
                "covered_tariff_codes": json.dumps(
                    payload.covered_tariff_codes, ensure_ascii=False
                ),
                "exemption_scope": json.dumps(
                    payload.exemption_scope, ensure_ascii=False
                ),
            },
        ).scalar_one()
        return str(approval_id)

    def approval_readiness(self, project_id: UUID | str) -> dict[str, Any]:
        items = self.requirements(project_id)
        mandatory = [
            item for item in items if item["requirement_type"] == "MANDATORY"
        ]
        missing = [
            item["requirement_code"]
            for item in mandatory
            if item["approval_status"] not in ("PROVIDED", "VERIFIED")
        ]
        return {
            "items": items,
            "mandatory_count": len(mandatory),
            "missing_mandatory_count": len(missing),
            "missing_requirement_codes": missing,
            "ready_for_preview": not missing,
        }

    def select_tariff(
        self,
        *,
        project_id: UUID | str,
        selection_scope: str,
        tariff_mapping_id: str | None,
        vehicle_tariff_rate_line_id: str | None,
        selected_by: str,
        selection_note: str | None,
    ) -> str:
        if bool(tariff_mapping_id) == bool(vehicle_tariff_rate_line_id):
            raise ValueError("Select exactly one tariff mapping or vehicle tariff line")
        selection_id = self._session.execute(
            text(
                """
                INSERT INTO enterprise.project_tariff_selection (
                  project_id,
                  selection_scope,
                  tariff_mapping_id,
                  vehicle_tariff_rate_line_id,
                  selected_by,
                  selection_note
                )
                VALUES (
                  :project_id,
                  :selection_scope,
                  :tariff_mapping_id,
                  :vehicle_tariff_rate_line_id,
                  :selected_by,
                  :selection_note
                )
                ON CONFLICT (project_id, selection_scope)
                DO UPDATE SET
                  tariff_mapping_id = EXCLUDED.tariff_mapping_id,
                  vehicle_tariff_rate_line_id = EXCLUDED.vehicle_tariff_rate_line_id,
                  selected_by = EXCLUDED.selected_by,
                  selection_note = EXCLUDED.selection_note,
                  verification_status = 'CANDIDATE',
                  updated_at = now()
                RETURNING project_tariff_selection_id
                """
            ),
            {
                "project_id": str(project_id),
                "selection_scope": selection_scope,
                "tariff_mapping_id": tariff_mapping_id,
                "vehicle_tariff_rate_line_id": vehicle_tariff_rate_line_id,
                "selected_by": selected_by,
                "selection_note": selection_note,
            },
        ).scalar_one()
        return str(selection_id)
