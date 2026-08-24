from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.calculation_engine import ComparisonResult, ScenarioResult


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _json_text(value: Any) -> str:
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class ComparisonPersistence:
    """Persist deterministic results without storing hidden model reasoning."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def persist(
        self,
        *,
        request_payload: dict[str, Any],
        result: ComparisonResult,
        engine_version: str,
        decision_project_id: UUID | str | None = None,
        vehicle_id: UUID | str | None = None,
        import_mode: str = "CKD",
        origin_country_iso2: str = "CN",
        scenario_code: str | None = None,
    ) -> dict[str, Any]:
        request_id = uuid4()
        scenario_input_id = uuid4()
        input_snapshot_id = uuid4()
        input_code = f"API-MY-{request_id}"
        safe_payload = {
            **request_payload,
            "request_id": str(request_id),
            "calculation_mode": "DETERMINISTIC_PERSISTED_RUN",
            "operational_use_permitted": False,
        }
        payload_text = _json_text(safe_payload)
        payload_sha256 = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()

        origin_country_iso2 = origin_country_iso2.upper()
        country_ids: dict[str, UUID] = {
            row["iso2"]: row["country_id"]
            for row in self._session.execute(
                text(
                    "SELECT iso2, country_id FROM ref.country "
                    "WHERE iso2 = ANY(:country_codes)"
                ),
                {"country_codes": ["MY", origin_country_iso2]},
            )
            .mappings()
            .all()
        }
        if "MY" not in country_ids or origin_country_iso2 not in country_ids:
            raise ValueError("Malaysia and the selected origin reference country are required")

        self._session.execute(
            text(
                """
                INSERT INTO enterprise.scenario_input (
                  scenario_input_id, scenario_code, country_id, vehicle_id,
                  import_date, import_mode, origin_country_id, input_payload,
                  record_status, decision_project_id
                ) VALUES (
                  :scenario_input_id, :scenario_code, :country_id, :vehicle_id,
                  :import_date, CAST(:import_mode AS ref.import_mode),
                  :origin_country_id, CAST(:payload AS jsonb), 'ACTIVE',
                  :decision_project_id
                )
                """
            ),
            {
                "scenario_input_id": scenario_input_id,
                "scenario_code": input_code,
                "country_id": country_ids["MY"],
                "vehicle_id": vehicle_id,
                "origin_country_id": country_ids[origin_country_iso2],
                "import_date": request_payload["import_date"],
                "import_mode": import_mode,
                "decision_project_id": decision_project_id,
                "payload": payload_text,
            },
        )
        self._session.execute(
            text(
                """
                INSERT INTO enterprise.input_snapshot (
                  input_snapshot_id, scenario_input_id, payload, payload_sha256
                ) VALUES (
                  :snapshot_id, :scenario_input_id, CAST(:payload AS jsonb), :sha256
                )
                """
            ),
            {
                "snapshot_id": input_snapshot_id,
                "scenario_input_id": scenario_input_id,
                "payload": payload_text,
                "sha256": payload_sha256,
            },
        )

        mapping_ids: dict[str, UUID] = {
            row["mapping_code"]: row["mapping_id"]
            for row in self._session.execute(
                text(
                    """
                    SELECT mapping_code, mapping_id
                    FROM customs.tariff_mapping
                    WHERE mapping_code = ANY(:mapping_codes)
                    """
                ),
                {
                    "mapping_codes": list(
                        {
                            line.mapping_code
                            for scenario in result.scenarios
                            for line in scenario.lines
                        }
                    )
                },
            )
            .mappings()
            .all()
        }
        sst_rule_id = self._session.execute(
            text(
                """
                SELECT rule_card_id
                FROM rules.country_rule_card
                WHERE rule_code = 'RULE-MY-SST-IMPORT-BASE-2018'
                  AND version = 1
                """
            )
        ).scalar_one()
        if scenario_code:
            selected_scenario_id = self._session.execute(
                text(
                    """
                    SELECT scenario_model_id
                    FROM rules.tax_scenario_model
                    WHERE scenario_code = :scenario_code
                      AND record_status = 'ACTIVE'
                    ORDER BY version DESC
                    LIMIT 1
                    """
                ),
                {"scenario_code": scenario_code},
            ).scalar_one_or_none()
            if selected_scenario_id is None:
                raise ValueError(f"Scenario model {scenario_code} not found")
            scenario_ids = {
                regime: selected_scenario_id for regime in ("MFN", "ACFTA", "RCEP")
            }
        else:
            scenario_ids = {
                row["regime"]: row["scenario_model_id"]
                for row in self._session.execute(
                    text(
                        """
                        SELECT
                          CASE
                            WHEN scenario_code LIKE '%ACFTA%' THEN 'ACFTA'
                            WHEN scenario_code LIKE '%RCEP%' THEN 'RCEP'
                            ELSE 'MFN'
                          END AS regime,
                          scenario_model_id
                        FROM rules.tax_scenario_model
                        WHERE scenario_code IN (
                          'SCN-MY-CKD-BEV-MFN-GOLDEN',
                          'SCN-MY-CKD-BEV-ACFTA-GOLDEN',
                          'SCN-MY-CKD-BEV-RCEP-GOLDEN'
                        )
                        """
                    )
                )
                .mappings()
                .all()
            }

        run_records: list[dict[str, Any]] = []
        for scenario in result.scenarios:
            run_id = uuid4()
            run_code = f"RUN-PY-MY-{request_id}-{scenario.requested_regime}"
            self._insert_run(
                run_id=run_id,
                run_code=run_code,
                scenario_model_id=scenario_ids[scenario.applied_regime],
                input_snapshot_id=input_snapshot_id,
                scenario=scenario,
                engine_version=engine_version,
            )
            self._insert_lines(
                run_id=run_id,
                scenario=scenario,
                mapping_ids=mapping_ids,
                sst_rule_id=sst_rule_id,
            )
            self._insert_trace(run_id=run_id, scenario=scenario)
            self._insert_missing(run_id=run_id, scenario=scenario)
            self._insert_llm_view(
                run_id=run_id,
                scenario_model_id=scenario_ids[scenario.applied_regime],
                input_snapshot_id=input_snapshot_id,
                scenario=scenario,
            )
            run_records.append(
                {
                    "calculation_run_id": str(run_id),
                    "run_code": run_code,
                    "requested_regime": scenario.requested_regime,
                    "applied_regime": scenario.applied_regime,
                    "completeness": scenario.completeness,
                }
            )
        return {
            "request_id": str(request_id),
            "scenario_input_id": str(scenario_input_id),
            "input_snapshot_id": str(input_snapshot_id),
            "runs": run_records,
        }

    def _insert_run(
        self,
        *,
        run_id: UUID,
        run_code: str,
        scenario_model_id: UUID,
        input_snapshot_id: UUID,
        scenario: ScenarioResult,
        engine_version: str,
    ) -> None:
        now = datetime.now(UTC)
        self._session.execute(
            text(
                """
                INSERT INTO calc.calculation_run (
                  calculation_run_id, run_code, scenario_model_id,
                  input_snapshot_id, rule_snapshot_at, engine_version,
                  run_status, completeness, currency_code, base_value,
                  gross_tax, recoverable_tax, net_tax, effective_tax_rate,
                  started_at, completed_at, error_summary
                ) VALUES (
                  :run_id, :run_code, :scenario_model_id, :input_snapshot_id,
                  :rule_snapshot_at, :engine_version, :run_status, :completeness,
                  :currency_code, :base_value, :gross_tax, :recoverable_tax,
                  :net_tax, :effective_tax_rate, :started_at, :completed_at,
                  :error_summary
                )
                """
            ),
            {
                "run_id": run_id,
                "run_code": run_code,
                "scenario_model_id": scenario_model_id,
                "input_snapshot_id": input_snapshot_id,
                "rule_snapshot_at": now,
                "engine_version": engine_version,
                "run_status": ("BLOCKED" if scenario.completeness == "BLOCKED" else "COMPLETE"),
                "completeness": scenario.completeness,
                "currency_code": scenario.currency_code,
                "base_value": scenario.customs_value,
                "gross_tax": scenario.gross_import_tax,
                "recoverable_tax": scenario.recoverable_tax,
                "net_tax": scenario.net_import_tax,
                "effective_tax_rate": scenario.effective_net_tax_rate,
                "started_at": now,
                "completed_at": now,
                "error_summary": (
                    None
                    if scenario.completeness != "BLOCKED"
                    else "Calculation blocked because a required mapping or rate is missing."
                ),
            },
        )

    def _insert_lines(
        self,
        *,
        run_id: UUID,
        scenario: ScenarioResult,
        mapping_ids: dict[str, UUID],
        sst_rule_id: UUID,
    ) -> None:
        sequence = 0
        for line in scenario.lines:
            expressions = (
                (
                    "IMPORT_DUTY",
                    line.customs_value,
                    line.duty_rate,
                    line.import_duty,
                    None,
                    mapping_ids[line.mapping_code],
                    {"op": "MULTIPLY", "base": "customs_value", "rate": "duty_rate"},
                ),
                (
                    "EXCISE_ASSESSMENT",
                    line.customs_value,
                    None,
                    line.excise_amount,
                    None,
                    None,
                    {
                        "op": "EXPLICIT_INPUT",
                        "legal_exemption_conclusion": False,
                    },
                ),
                (
                    "SST",
                    line.sst_base,
                    line.sst_rate,
                    line.sst_amount,
                    sst_rule_id,
                    mapping_ids[line.mapping_code],
                    {
                        "op": "MULTIPLY",
                        "base": "customs_value_plus_duty_plus_excise",
                        "rate": "sst_rate",
                    },
                ),
            )
            for (
                tax_type,
                base,
                rate,
                amount,
                rule_id,
                mapping_id,
                expression,
            ) in expressions:
                sequence += 1
                self._session.execute(
                    text(
                        """
                        INSERT INTO calc.calculation_line (
                          calculation_run_id, sequence_no, tax_code,
                          base_expression, base_amount, rate_type, rate,
                          tax_expression, gross_tax_amount,
                          recoverable_fraction, net_tax_amount, rule_card_id,
                          tariff_mapping_id, line_status, notes
                        ) VALUES (
                          :run_id, :sequence_no, :tax_code,
                          CAST(:base_expression AS jsonb), :base_amount,
                          :rate_type, :rate, CAST(:tax_expression AS jsonb),
                          :gross_tax_amount, :recoverable_fraction,
                          :net_tax_amount, :rule_card_id, :mapping_id,
                          'COMPLETE', :notes
                        )
                        """
                    ),
                    {
                        "run_id": run_id,
                        "sequence_no": sequence,
                        "tax_code": f"{tax_type}:{line.ccu_code}",
                        "base_expression": _json_text({"ref": "item", "ccu_code": line.ccu_code}),
                        "base_amount": base,
                        "rate_type": (
                            "NOT_APPLICABLE"
                            if rate is None
                            else ("ZERO" if rate == 0 else "AD_VALOREM")
                        ),
                        "rate": rate,
                        "tax_expression": _json_text(expression),
                        "gross_tax_amount": amount,
                        "recoverable_fraction": (
                            line.recoverable_tax / line.sst_amount
                            if tax_type == "SST" and line.sst_amount
                            else Decimal("0")
                        ),
                        "net_tax_amount": (
                            amount - line.recoverable_tax if tax_type == "SST" else amount
                        ),
                        "rule_card_id": rule_id,
                        "mapping_id": mapping_id,
                        "notes": (
                            f"Python engine; requested={scenario.requested_regime}; "
                            f"applied={scenario.applied_regime}; mapping_status="
                            f"{line.verification_status}"
                        ),
                    },
                )

    def _insert_trace(self, *, run_id: UUID, scenario: ScenarioResult) -> None:
        trace_rows = (
            (
                "INPUT_VALIDATION",
                "Was a versioned input snapshot created?",
                {"snapshot_created": True, "operational_use_permitted": False},
            ),
            (
                "SCENARIO_SELECTION",
                "Which origin regime was applied?",
                {
                    "requested_regime": scenario.requested_regime,
                    "applied_regime": scenario.applied_regime,
                    "fallback_applied": scenario.fallback_applied,
                },
            ),
            (
                "CLASSIFICATION",
                "Which explicit mappings were used?",
                {
                    "mappings": [
                        {
                            "ccu_code": line.ccu_code,
                            "mapping_code": line.mapping_code,
                            "status": line.verification_status,
                        }
                        for line in scenario.lines
                    ]
                },
            ),
            (
                "ELIGIBILITY",
                "Was preferential eligibility accepted?",
                {
                    "preference_applied": (scenario.applied_regime == scenario.requested_regime),
                    "fallback_applied": scenario.fallback_applied,
                },
            ),
            (
                "RULE_SELECTION",
                "Which calculation sequence was used?",
                {"sequence": ["IMPORT_DUTY", "EXCISE_ASSESSMENT", "SST"]},
            ),
            (
                "CALCULATION",
                "What tax and profit results were produced?",
                {
                    "gross_import_tax": scenario.gross_import_tax,
                    "net_import_tax": scenario.net_import_tax,
                    "effective_net_tax_rate": scenario.effective_net_tax_rate,
                    "gross_profit": scenario.gross_profit,
                    "gross_profit_margin": scenario.gross_profit_margin,
                },
            ),
            (
                "RISK_ASSESSMENT",
                "What prevents unqualified operational use?",
                {
                    "completeness": scenario.completeness,
                    "missing_data_count": len(scenario.missing_data),
                    "warnings": scenario.warnings,
                },
            ),
        )
        source_refs = [
            {"source_clause_id": evidence.source_clause_id}
            for line in scenario.lines
            for evidence in line.evidence
        ]
        for sequence, (step_type, question, result) in enumerate(trace_rows, 1):
            self._session.execute(
                text(
                    """
                    INSERT INTO audit.decision_trace (
                      calculation_run_id, sequence_no, step_type,
                      decision_question, input_record_refs, rule_record_refs,
                      source_clause_refs, explicit_rationale, result,
                      confidence, human_review_required
                    ) VALUES (
                      :run_id, :sequence_no, :step_type, :question,
                      '[]'::jsonb, '[]'::jsonb, CAST(:source_refs AS jsonb),
                      :rationale, CAST(:result AS jsonb), :confidence,
                      :human_review_required
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "sequence_no": sequence,
                    "step_type": step_type,
                    "question": question,
                    "source_refs": _json_text(source_refs),
                    "rationale": (
                        "Explicit deterministic business result; no hidden model "
                        "chain-of-thought is stored."
                    ),
                    "result": _json_text(result),
                    "confidence": (
                        Decimal("0.95") if scenario.completeness == "COMPLETE" else Decimal("0.80")
                    ),
                    "human_review_required": scenario.completeness != "COMPLETE",
                },
            )

    def _insert_missing(self, *, run_id: UUID, scenario: ScenarioResult) -> None:
        for missing in scenario.missing_data:
            self._session.execute(
                text(
                    """
                    INSERT INTO audit.missing_data (
                      missing_data_id, calculation_run_id, field_path,
                      description, data_owner, data_kind, data_ownership,
                      blocking_scope, priority, next_action, status
                    ) VALUES (
                      :id, :run_id, :field_path, :description, :owner,
                      'ENTERPRISE_INPUT', 'MIXED', :blocking_scope,
                      :priority, :next_action, 'WAITING_ENTERPRISE'
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "run_id": run_id,
                    "field_path": missing.field_path,
                    "description": missing.description,
                    "owner": missing.owner,
                    "blocking_scope": missing.blocking_scope,
                    "priority": missing.priority,
                    "next_action": "Provide or verify the identified input, then rerun.",
                },
            )

    def _insert_llm_view(
        self,
        *,
        run_id: UUID,
        scenario_model_id: UUID,
        input_snapshot_id: UUID,
        scenario: ScenarioResult,
    ) -> None:
        rows = (
            (
                "SCENARIO_MODEL",
                scenario_model_id,
                {
                    "requested_regime": scenario.requested_regime,
                    "applied_regime": scenario.applied_regime,
                    "fallback_applied": scenario.fallback_applied,
                },
                "Explain scenario selection and fallback.",
            ),
            (
                "CALCULATION_RUN",
                run_id,
                {
                    "gross_import_tax": scenario.gross_import_tax,
                    "effective_net_tax_rate": scenario.effective_net_tax_rate,
                    "gross_profit": scenario.gross_profit,
                    "gross_profit_margin": scenario.gross_profit_margin,
                    "completeness": scenario.completeness,
                },
                "Explain stored deterministic tax and profit outputs.",
            ),
            (
                "INPUT_SNAPSHOT",
                input_snapshot_id,
                {
                    "operational_use_permitted": False,
                    "missing_data_count": len(scenario.missing_data),
                },
                "Explain limitations without inventing missing inputs.",
            ),
        )
        for sequence, (record_type, record_id, fields, why_read) in enumerate(rows, 1):
            self._session.execute(
                text(
                    """
                    INSERT INTO ai.llm_view_item (
                      calculation_run_id, sequence_no, record_type, record_id,
                      field_subset, why_read, source_clause_refs, data_quality,
                      prompt_safe
                    ) VALUES (
                      :run_id, :sequence_no, :record_type, :record_id,
                      CAST(:fields AS jsonb), :why_read, '[]'::jsonb,
                      :data_quality, true
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "sequence_no": sequence,
                    "record_type": record_type,
                    "record_id": record_id,
                    "fields": _json_text(fields),
                    "why_read": why_read,
                    "data_quality": (
                        "VERIFIED" if scenario.completeness == "COMPLETE" else "CANDIDATE"
                    ),
                },
            )
