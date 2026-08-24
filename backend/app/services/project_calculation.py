from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.decision_repository import DecisionRepository


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
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


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, dict) or isinstance(value, list):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


class ProjectCalculationService:
    """Project-level deterministic calculation and auditable persistence.

    It currently executes the verified whole-vehicle CBU tax chain. Other routes
    return structured partial or blocked results until a project BOM/CCU
    allocation and the local finished-vehicle rate inputs exist.
    """

    engine_version = "project-five-route-0.3.0"

    def __init__(self, session: Session) -> None:
        self._session = session
        self._decisions = DecisionRepository(session)

    def preview(self, project_id: UUID | str) -> dict[str, Any]:
        project = self._decisions.get_project(project_id)
        inputs = self._decisions.project_inputs(project_id)
        completion = self._decisions.completion(project_id)
        approvals = self._decisions.approval_readiness(project_id)
        input_map = {item["field_path"]: item for item in inputs}
        missing: list[dict[str, Any]] = []
        warnings: list[str] = []

        for item in inputs:
            if item["value_status"] not in ("PROVIDED", "VERIFIED"):
                missing.append(
                    self._missing(
                        field_path=item["field_path"],
                        description="该路径要求的企业字段尚未提供或未达到可使用状态。",
                        owner="ENTERPRISE",
                        return_step=3,
                    )
                )
        for code in approvals["missing_requirement_codes"]:
            missing.append(
                self._missing(
                    field_path=f"approval.{code}",
                    description="强制审批尚未提供，不能进入正式税额计算。",
                    owner="ENTERPRISE_APPROVAL_OWNER",
                    return_step=3,
                )
            )

        selection = self._selected_vehicle_tariff(project_id)
        route_code = project["selected_route_code"]
        if selection is None:
            missing.append(
                self._missing(
                    field_path="classification.vehicle_tariff_selection",
                    description="尚未保存明确的整车或整套CKD税率行选择。",
                    owner="CUSTOMS_CLASSIFICATION_OWNER",
                    return_step=4,
                )
            )

        gate = {
            "enterprise_inputs": completion,
            "approvals": {
                "mandatory_count": approvals["mandatory_count"],
                "missing_mandatory_count": approvals["missing_mandatory_count"],
                "missing_requirement_codes": approvals["missing_requirement_codes"],
            },
            "tariff_selection_saved": selection is not None,
        }
        base_response: dict[str, Any] = {
            "project_id": str(project["project_id"]),
            "project_code": project["project_code"],
            "route_code": route_code,
            "route_name": self._route_name(route_code),
            "calculation_date": project["calculation_date"],
            "currency_code": "MYR",
            "engine_version": self.engine_version,
            "gate": gate,
            "input_snapshot_preview": self._snapshot_payload(
                project=project,
                inputs=inputs,
                approvals=approvals,
                selection=selection,
            ),
        }

        if route_code not in (
            "ROUTE-MY-01-CBU",
            "ROUTE-MY-02-CKD-WHOLE-KIT",
        ):
            missing.append(
                self._missing(
                    field_path="shipment.project_bom_ccu_allocation",
                    description=(
                        "该路径需要项目级BOM、装箱行、CCU映射和逐行价值分配；"
                        "当前决策项目尚未建立这些结构化记录。"
                    ),
                    owner="ENTERPRISE_CUSTOMS_AND_ENGINEERING",
                    return_step=4,
                )
            )
            return {
                **base_response,
                "status": "BLOCKED",
                "calculation_scope": "NO_TAX_AMOUNT",
                "totals": None,
                "lines": [],
                "missing_data": self._deduplicate_missing(missing),
                "warnings": warnings,
                "operational_use_permitted": False,
            }

        if missing or selection is None:
            return {
                **base_response,
                "status": "BLOCKED",
                "calculation_scope": "NO_TAX_AMOUNT",
                "totals": None,
                "lines": [],
                "missing_data": self._deduplicate_missing(missing),
                "warnings": warnings,
                "operational_use_permitted": False,
            }

        if route_code == "ROUTE-MY-01-CBU":
            return self._preview_cbu(
                base_response=base_response,
                project=project,
                input_map=input_map,
                approvals=approvals,
                selection=selection,
                missing=missing,
                warnings=warnings,
            )
        return self._preview_ckd(
            base_response=base_response,
            project=project,
            input_map=input_map,
            approvals=approvals,
            selection=selection,
            missing=missing,
            warnings=warnings,
        )

    def run(self, project_id: UUID | str) -> dict[str, Any]:
        preview = self.preview(project_id)
        if preview["status"] == "BLOCKED":
            raise ValueError(
                "Calculation is blocked: "
                + "; ".join(item["field_path"] for item in preview["missing_data"])
            )
        project = self._decisions.get_project(project_id)
        selection = self._selected_vehicle_tariff(project_id)
        if selection is None:
            raise ValueError("Vehicle tariff selection is required")

        snapshot_payload = {
            **preview["input_snapshot_preview"],
            "preview_result": {
                "status": preview["status"],
                "totals": preview["totals"],
                "lines": preview["lines"],
                "missing_data": preview["missing_data"],
                "warnings": preview["warnings"],
            },
            "operational_use_permitted": preview["status"] == "COMPLETE",
        }
        payload_text = _json_text(snapshot_payload)
        payload_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        scenario_input_id = uuid4()
        snapshot_id = uuid4()
        run_id = uuid4()
        now = datetime.now(UTC)
        scenario_model_id = self._scenario_model_id(preview["route_code"])
        country_id = self._country_id("MY")
        origin_iso2 = str(
            preview["input_snapshot_preview"]["input_values"].get(
                "origin.country_iso2", "CN"
            )
        ).upper()
        origin_country_id = self._country_id(origin_iso2)
        import_mode = self._route_import_mode(preview["route_code"])
        run_code = f"RUN-MY-PROJECT-{project['project_code']}-{now:%Y%m%d%H%M%S%f}"

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
                  :origin_country_id, CAST(:payload AS jsonb), 'ACTIVE', :project_id
                )
                """
            ),
            {
                "scenario_input_id": scenario_input_id,
                "scenario_code": f"PROJECT-{project['project_code']}-{run_id}",
                "country_id": country_id,
                "vehicle_id": project["vehicle_id"],
                "import_date": project["calculation_date"],
                "import_mode": import_mode,
                "origin_country_id": origin_country_id,
                "payload": payload_text,
                "project_id": project["project_id"],
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
                "snapshot_id": snapshot_id,
                "scenario_input_id": scenario_input_id,
                "payload": payload_text,
                "sha256": payload_hash,
            },
        )
        totals = preview["totals"]
        self._session.execute(
            text(
                """
                INSERT INTO calc.calculation_run (
                  calculation_run_id, run_code, scenario_model_id,
                  input_snapshot_id, rule_snapshot_at, engine_version,
                  run_status, completeness, currency_code, base_value,
                  gross_tax, recoverable_tax, net_tax, effective_tax_rate,
                  started_at, completed_at
                ) VALUES (
                  :run_id, :run_code, :scenario_model_id, :snapshot_id,
                  :rule_snapshot_at, :engine_version,
                  CAST(:run_status AS ref.calculation_status),
                  CAST(:completeness AS ref.completeness), 'MYR', :base_value,
                  :gross_tax, 0, :net_tax, :effective_tax_rate, :started_at, :completed_at
                )
                """
            ),
            {
                "run_id": run_id,
                "run_code": run_code,
                "scenario_model_id": scenario_model_id,
                "snapshot_id": snapshot_id,
                "rule_snapshot_at": now,
                "engine_version": self.engine_version,
                "run_status": preview["status"],
                "completeness": preview["status"],
                "base_value": totals["customs_value"],
                "gross_tax": totals["gross_tax"],
                "net_tax": totals["net_tax"],
                "effective_tax_rate": totals["effective_tax_rate"],
                "started_at": now,
                "completed_at": now,
            },
        )
        rule_id = self._rule_id("RULE-MY-CBU-TAX-CHAIN-CORRECTED")
        for line in preview["lines"]:
            self._session.execute(
                text(
                    """
                    INSERT INTO calc.calculation_line (
                      calculation_run_id, sequence_no, tax_code,
                      base_expression, base_amount, rate_type, rate,
                      tax_expression, gross_tax_amount, recoverable_fraction,
                      net_tax_amount, rule_card_id, vehicle_tariff_rate_line_id,
                      line_status, notes
                    ) VALUES (
                      :run_id, :sequence_no, :tax_code,
                      CAST(:base_expression AS jsonb), :base_amount,
                      CAST(:rate_type AS ref.rate_type), :rate,
                      CAST(:tax_expression AS jsonb), :amount, 0, :amount,
                      :rule_id, :vehicle_tariff_id,
                      CAST(:line_status AS ref.calculation_status), :notes
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "sequence_no": line["sequence_no"],
                    "tax_code": line["tax_code"],
                    "base_expression": _json_text(line["base_expression"]),
                    "base_amount": line["base_amount"],
                    "rate_type": "ZERO" if Decimal(line["rate"]) == 0 else "AD_VALOREM",
                    "rate": line["rate"],
                    "tax_expression": _json_text(line["tax_expression"]),
                    "amount": line["amount"],
                    "rule_id": rule_id,
                    "vehicle_tariff_id": selection["vehicle_tariff_rate_line_id"],
                    "line_status": preview["status"],
                    "notes": line["display_formula"],
                },
            )
        self._insert_trace(run_id=run_id, preview=preview, selection=selection)
        self._insert_missing(run_id=run_id, items=preview["missing_data"])
        self._insert_llm_view(
            run_id=run_id,
            scenario_model_id=scenario_model_id,
            snapshot_id=snapshot_id,
            preview=preview,
        )
        return {
            "calculation_run_id": str(run_id),
            "run_code": run_code,
            "preview": preview,
        }

    def get_run(self, run_id: UUID | str) -> dict[str, Any]:
        run = self._session.execute(
            text(
                """
                SELECT
                  run.calculation_run_id, run.run_code, run.engine_version,
                  run.run_status::text AS run_status,
                  run.completeness::text AS completeness, run.currency_code,
                  run.base_value, run.gross_tax, run.recoverable_tax, run.net_tax,
                  run.effective_tax_rate, run.rule_snapshot_at, run.completed_at,
                  scenario.scenario_code, input.decision_project_id,
                  project.project_code, project.project_name,
                  route.route_code, route.route_name_cn
                FROM calc.calculation_run run
                JOIN rules.tax_scenario_model scenario
                  ON scenario.scenario_model_id = run.scenario_model_id
                JOIN enterprise.input_snapshot snapshot
                  ON snapshot.input_snapshot_id = run.input_snapshot_id
                JOIN enterprise.scenario_input input
                  ON input.scenario_input_id = snapshot.scenario_input_id
                LEFT JOIN enterprise.decision_project project
                  ON project.project_id = input.decision_project_id
                LEFT JOIN rules.vehicle_tax_route route
                  ON route.route_code = project.selected_route_code
                WHERE run.calculation_run_id = :run_id
                """
            ),
            {"run_id": str(run_id)},
        ).mappings().one_or_none()
        if run is None:
            raise ValueError(f"Calculation run {run_id} not found")
        lines = [
            dict(row)
            for row in self._session.execute(
                text(
                    """
                    SELECT sequence_no, tax_code, base_expression, base_amount,
                           rate_type::text AS rate_type, rate, tax_expression,
                           gross_tax_amount AS amount, recoverable_fraction,
                           net_tax_amount,
                           line_status::text AS line_status, notes
                    FROM calc.calculation_line
                    WHERE calculation_run_id = :run_id
                    ORDER BY sequence_no
                    """
                ),
                {"run_id": str(run_id)},
            ).mappings()
        ]
        return {"run": dict(run), "lines": lines}

    def get_trace(self, run_id: UUID | str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    """
                    SELECT sequence_no, step_type::text AS step_type,
                           decision_question, input_record_refs, rule_record_refs,
                           source_clause_refs, explicit_rationale, result,
                           confidence, human_review_required, created_at
                    FROM audit.decision_trace
                    WHERE calculation_run_id = :run_id
                    ORDER BY sequence_no
                    """
                ),
                {"run_id": str(run_id)},
            ).mappings()
        ]

    def get_missing(self, run_id: UUID | str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    """
                    SELECT field_path, description, data_owner,
                           data_kind::text AS data_kind,
                           data_ownership::text AS data_ownership,
                           blocking_scope, priority::text AS priority,
                           next_action, status::text AS status
                    FROM audit.missing_data
                    WHERE calculation_run_id = :run_id
                    ORDER BY priority, field_path
                    """
                ),
                {"run_id": str(run_id)},
            ).mappings()
        ]

    def _preview_cbu(
        self,
        *,
        base_response: dict[str, Any],
        project: dict[str, Any],
        input_map: dict[str, dict[str, Any]],
        approvals: dict[str, Any],
        selection: dict[str, Any],
        missing: list[dict[str, Any]],
        warnings: list[str],
    ) -> dict[str, Any]:
        customs_value = _decimal(input_map["vehicle.customs_value"]["value_payload"])
        if customs_value is None or customs_value <= 0:
            missing.append(
                self._missing(
                    "vehicle.customs_value",
                    "整车海关价值必须是大于0的数值。",
                    "ENTERPRISE_FINANCE_OWNER",
                    3,
                )
            )
        duty_rate = _decimal(selection["import_duty_rate"])
        excise_rate = _decimal(selection["excise_duty_rate"])
        sst_rate = _decimal(selection["sales_tax_rate"])
        for field_path, rate_value, description in (
            ("rate.import_duty", duty_rate, "所选税率行缺少进口关税率。"),
            ("rate.excise", excise_rate, "所选税率行缺少可执行的消费税率。"),
            ("rate.sst", sst_rate, "所选税率行缺少销售税率。"),
        ):
            if rate_value is None:
                missing.append(
                    self._missing(field_path, description, "PUBLIC_POLICY_OWNER", 4)
                )
        if selection["origin_regime"] == "FTA":
            fta_item = next(
                (
                    item
                    for item in approvals["items"]
                    if item["requirement_code"]
                    == "REQ-MY-FTA-SHIPMENT-ORIGIN-PROOF"
                ),
                None,
            )
            if fta_item is None or fta_item["approval_status"] not in (
                "PROVIDED",
                "VERIFIED",
            ):
                missing.append(
                    self._missing(
                        "origin.preference_evidence_if_claimed",
                        "已选择FTA税率，但原产地优惠证明尚未提供；请选择MFN或补充证明。",
                        "ENTERPRISE_FTA_OWNER",
                        3,
                    )
                )
        if missing or customs_value is None or None in (duty_rate, excise_rate, sst_rate):
            return {
                **base_response,
                "status": "BLOCKED",
                "calculation_scope": "NO_TAX_AMOUNT",
                "totals": None,
                "lines": [],
                "missing_data": self._deduplicate_missing(missing),
                "warnings": warnings,
                "operational_use_permitted": False,
            }
        duty = _money(customs_value * duty_rate)
        excise_base = _money(customs_value + duty)
        excise = _money(excise_base * excise_rate)
        sst_base = _money(customs_value + duty + excise)
        sst = _money(sst_base * sst_rate)
        gross = _money(duty + excise + sst)
        status = (
            "COMPLETE"
            if selection["verification_status"] in ("VERIFIED", "RULING_CONFIRMED")
            else "PARTIAL"
        )
        if status == "PARTIAL":
            warnings.append("所选税率行仍为候选状态，正式业务使用前需要人工复核。")
        lines = [
            self._line(
                1,
                "IMPORT_DUTY",
                customs_value,
                duty_rate,
                duty,
                {"ref": "vehicle.customs_value"},
                {
                    "op": "MULTIPLY",
                    "args": [
                        {"ref": "vehicle.customs_value"},
                        {"ref": "rate.import_duty"},
                    ],
                },
                "海关价值 × 进口关税率",
                selection,
            ),
            self._line(
                2,
                "EXCISE",
                excise_base,
                excise_rate,
                excise,
                {
                    "op": "ADD",
                    "args": [
                        {"ref": "vehicle.customs_value"},
                        {"ref": "tax.import_duty"},
                    ],
                },
                {
                    "op": "MULTIPLY",
                    "args": [
                        {"ref": "tax.excise_base"},
                        {"ref": "rate.excise"},
                    ],
                },
                "（海关价值＋进口关税）× 消费税率",
                selection,
            ),
            self._line(
                3,
                "SST",
                sst_base,
                sst_rate,
                sst,
                {
                    "op": "ADD",
                    "args": [
                        {"ref": "vehicle.customs_value"},
                        {"ref": "tax.import_duty"},
                        {"ref": "tax.excise"},
                    ],
                },
                {
                    "op": "MULTIPLY",
                    "args": [{"ref": "tax.sst_base"}, {"ref": "rate.sst"}],
                },
                "（海关价值＋进口关税＋消费税）× 销售税率",
                selection,
            ),
        ]
        return {
            **base_response,
            "status": status,
            "calculation_scope": "CBU_BORDER_TAX_CHAIN",
            "totals": {
                "customs_value": _money(customs_value),
                "gross_tax": gross,
                "recoverable_tax": Decimal("0"),
                "net_tax": gross,
                "effective_tax_rate": _rate(gross / customs_value),
                "landed_value_before_other_costs": _money(customs_value + gross),
            },
            "lines": lines,
            "missing_data": [],
            "warnings": warnings,
            "operational_use_permitted": status == "COMPLETE",
        }

    def _preview_ckd(
        self,
        *,
        base_response: dict[str, Any],
        project: dict[str, Any],
        input_map: dict[str, dict[str, Any]],
        approvals: dict[str, Any],
        selection: dict[str, Any],
        missing: list[dict[str, Any]],
        warnings: list[str],
    ) -> dict[str, Any]:
        customs_value = _decimal(
            input_map["import.ckd_kit_customs_value"]["value_payload"]
        )
        duty_rate = _decimal(selection["import_duty_rate"])
        sst_rate = _decimal(selection["sales_tax_rate"])
        if customs_value is None or customs_value <= 0:
            missing.append(
                self._missing(
                    "import.ckd_kit_customs_value",
                    "CKD套件海关价值必须是大于0的数值。",
                    "ENTERPRISE_FINANCE_OWNER",
                    3,
                )
            )
        if duty_rate is None:
            missing.append(
                self._missing(
                    "rate.import_duty",
                    "所选CKD税率行缺少进口关税率。",
                    "PUBLIC_POLICY_OWNER",
                    4,
                )
            )
        if sst_rate is None:
            missing.append(
                self._missing(
                    "rate.import_sst",
                    "所选CKD税率行缺少进口销售税率。",
                    "PUBLIC_POLICY_OWNER",
                    4,
                )
            )
        exemption_verified = any(
            item["requirement_code"]
            in (
                "REQ-MY-CKD-BEV-TAX-EXEMPTION-CONFIRMATION",
                "REQ-MY-LOCAL-BEV-EXEMPTION-CONFIRMATION",
            )
            and item["approval_status"] == "VERIFIED"
            for item in approvals["items"]
        )
        if not exemption_verified:
            missing.extend(
                [
                    self._missing(
                        "rate.local_excise",
                        "未验证本地BEV豁免，且项目尚未提供本地成车法定消费税率。",
                        "PUBLIC_TAX_OWNER",
                        3,
                    ),
                    self._missing(
                        "rate.local_sst",
                        "未验证本地BEV豁免，且项目尚未提供本地成车法定销售税率。",
                        "PUBLIC_TAX_OWNER",
                        3,
                    ),
                ]
            )
        if customs_value is None or duty_rate is None or sst_rate is None:
            return {
                **base_response,
                "status": "BLOCKED",
                "calculation_scope": "NO_TAX_AMOUNT",
                "totals": None,
                "lines": [],
                "missing_data": self._deduplicate_missing(missing),
                "warnings": warnings,
                "operational_use_permitted": False,
            }
        duty = _money(customs_value * duty_rate)
        import_sst_base = _money(customs_value + duty)
        import_sst = _money(import_sst_base * sst_rate)
        gross = _money(duty + import_sst)
        lines = [
            self._line(
                1,
                "IMPORT_DUTY",
                customs_value,
                duty_rate,
                duty,
                {"ref": "import.ckd_kit_customs_value"},
                {"op": "MULTIPLY", "args": [{"ref": "import.ckd_kit_customs_value"}, {"ref": "rate.import_duty"}]},
                "CKD套件海关价值 × 进口关税率",
                selection,
            ),
            self._line(
                2,
                "IMPORT_SST",
                import_sst_base,
                sst_rate,
                import_sst,
                {"op": "ADD", "args": [{"ref": "import.ckd_kit_customs_value"}, {"ref": "tax.import_duty"}]},
                {"op": "MULTIPLY", "args": [{"ref": "tax.import_sst_base"}, {"ref": "rate.import_sst"}]},
                "（CKD套件海关价值＋进口关税）× 进口销售税率",
                selection,
            ),
        ]
        if exemption_verified:
            lines.extend(
                [
                    self._line(3, "LOCAL_EXCISE", _decimal(input_map["local.excise_value"]["value_payload"]) or Decimal("0"), Decimal("0"), Decimal("0"), {"ref": "local.excise_value"}, {"op": "MULTIPLY", "args": [{"ref": "local.excise_value"}, {"const": 0}]}, "已验证项目豁免：本地成车消费税率0", selection),
                    self._line(4, "LOCAL_SST", _decimal(input_map["local.sales_tax_value"]["value_payload"]) or Decimal("0"), Decimal("0"), Decimal("0"), {"ref": "local.sales_tax_value"}, {"op": "MULTIPLY", "args": [{"ref": "local.sales_tax_value"}, {"const": 0}]}, "已验证项目豁免：本地成车销售税率0", selection),
                ]
            )
        status = "COMPLETE" if exemption_verified and not missing else "PARTIAL"
        if not exemption_verified:
            warnings.append("目前只计算CKD进口环节已知税额；本地成车税负尚未完整。")
        return {
            **base_response,
            "status": status,
            "calculation_scope": (
                "CKD_IMPORT_AND_LOCAL_FINISHED_TAX"
                if exemption_verified
                else "CKD_IMPORT_TAX_ONLY"
            ),
            "totals": {
                "customs_value": _money(customs_value),
                "gross_tax": gross,
                "recoverable_tax": Decimal("0"),
                "net_tax": gross,
                "effective_tax_rate": _rate(gross / customs_value),
                "landed_value_before_other_costs": _money(customs_value + gross),
            },
            "lines": lines,
            "missing_data": self._deduplicate_missing(missing),
            "warnings": warnings,
            "operational_use_permitted": status == "COMPLETE",
        }

    def _selected_vehicle_tariff(self, project_id: UUID | str) -> dict[str, Any] | None:
        row = self._session.execute(
            text(
                """
                SELECT
                  selection.project_tariff_selection_id,
                  line.vehicle_tariff_rate_line_id,
                  line.rate_line_code, line.national_tariff_code,
                  line.origin_regime::text AS origin_regime,
                  agreement.agreement_code, line.import_duty_rate,
                  line.excise_duty_rate, line.sales_tax_rate,
                  line.sales_tax_treatment, line.excise_treatment,
                  line.verification_status::text AS verification_status,
                  line.tariff_source_clause_id::text AS tariff_source_clause_id,
                  line.tax_treatment_source_clause_id::text
                    AS tax_treatment_source_clause_id,
                  source.source_code, clause.locator_value AS source_locator
                FROM enterprise.project_tariff_selection selection
                JOIN customs.vehicle_tariff_rate_line line
                  ON line.vehicle_tariff_rate_line_id =
                     selection.vehicle_tariff_rate_line_id
                LEFT JOIN ref.trade_agreement agreement
                  ON agreement.trade_agreement_id = line.trade_agreement_id
                JOIN evidence.source_clause clause
                  ON clause.source_clause_id = line.tariff_source_clause_id
                JOIN evidence.source_document source
                  ON source.source_document_id = clause.source_document_id
                WHERE selection.project_id = :project_id
                  AND selection.selection_scope = 'vehicle'
                """
            ),
            {"project_id": str(project_id)},
        ).mappings().one_or_none()
        return dict(row) if row else None

    def _snapshot_payload(
        self,
        *,
        project: dict[str, Any],
        inputs: list[dict[str, Any]],
        approvals: dict[str, Any],
        selection: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "project": project,
            "input_values": {
                item["field_path"]: item["value_payload"] for item in inputs
            },
            "input_statuses": {
                item["field_path"]: item["value_status"] for item in inputs
            },
            "approvals": [
                {
                    "requirement_code": item["requirement_code"],
                    "requirement_type": item["requirement_type"],
                    "approval_status": item["approval_status"],
                    "approval_reference": item["approval_reference"],
                }
                for item in approvals["items"]
            ],
            "tariff_selection": selection,
        }

    @staticmethod
    def _missing(
        field_path: str,
        description: str,
        owner: str,
        return_step: int,
    ) -> dict[str, Any]:
        return {
            "field_path": field_path,
            "description": description,
            "data_owner": owner,
            "data_kind": (
                "PUBLIC_RESEARCH"
                if owner in ("PUBLIC_POLICY_OWNER", "PUBLIC_TAX_OWNER")
                else "ENTERPRISE_INPUT"
            ),
            "data_ownership": (
                "PUBLIC"
                if owner in ("PUBLIC_POLICY_OWNER", "PUBLIC_TAX_OWNER")
                else "ENTERPRISE"
            ),
            "blocking_scope": "PROJECT_CALCULATION",
            "priority": "P0",
            "next_action": "补充或验证该字段后重新Preview。",
            "return_step": return_step,
        }

    @staticmethod
    def _deduplicate_missing(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return list({item["field_path"]: item for item in items}.values())

    @staticmethod
    def _line(
        sequence_no: int,
        tax_code: str,
        base: Decimal,
        rate: Decimal,
        amount: Decimal,
        base_expression: dict[str, Any],
        tax_expression: dict[str, Any],
        display_formula: str,
        selection: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "sequence_no": sequence_no,
            "tax_code": tax_code,
            "base_amount": _money(base),
            "rate": _rate(rate),
            "amount": _money(amount),
            "base_expression": base_expression,
            "tax_expression": tax_expression,
            "display_formula": display_formula,
            "national_tariff_code": selection["national_tariff_code"],
            "rate_line_code": selection["rate_line_code"],
            "verification_status": selection["verification_status"],
            "source": {
                "source_code": selection["source_code"],
                "source_locator": selection["source_locator"],
                "source_clause_id": selection["tariff_source_clause_id"],
            },
        }

    def _insert_trace(
        self,
        *,
        run_id: UUID,
        preview: dict[str, Any],
        selection: dict[str, Any],
    ) -> None:
        rows = (
            ("INPUT_VALIDATION", "哪些项目输入进入了不可变快照？", {"gate": preview["gate"]}),
            ("SCENARIO_SELECTION", "系统选择了哪条进口税务路径？", {"route_code": preview["route_code"], "scope": preview["calculation_scope"]}),
            ("CLASSIFICATION", "使用了哪一条显式税率行？", {"rate_line_code": selection["rate_line_code"], "national_tariff_code": selection["national_tariff_code"], "verification_status": selection["verification_status"]}),
            ("ELIGIBILITY", "优惠及强制审批是否达到当前计算条件？", {"approvals": preview["input_snapshot_preview"]["approvals"], "origin_regime": selection["origin_regime"], "agreement_code": selection["agreement_code"]}),
            ("RULE_SELECTION", "采用了什么法定计算顺序？", {"sequence": [line["tax_code"] for line in preview["lines"]]}),
            ("CALCULATION", "逐项税额和综合税率是多少？", {"totals": preview["totals"], "lines": preview["lines"]}),
            ("RISK_ASSESSMENT", "结果是否允许直接用于业务？", {"status": preview["status"], "operational_use_permitted": preview["operational_use_permitted"], "warnings": preview["warnings"], "missing_data": preview["missing_data"]}),
        )
        source_refs = [
            {"source_clause_id": selection["tariff_source_clause_id"]},
        ]
        if selection["tax_treatment_source_clause_id"]:
            source_refs.append(
                {"source_clause_id": selection["tax_treatment_source_clause_id"]}
            )
        for sequence_no, (step_type, question, result) in enumerate(rows, 1):
            self._session.execute(
                text(
                    """
                    INSERT INTO audit.decision_trace (
                      calculation_run_id, sequence_no, step_type,
                      decision_question, input_record_refs, rule_record_refs,
                      source_clause_refs, explicit_rationale, result,
                      confidence, human_review_required
                    ) VALUES (
                      :run_id, :sequence_no,
                      CAST(:step_type AS ref.decision_step_type), :question,
                      CAST(:input_refs AS jsonb), CAST(:rule_refs AS jsonb),
                      CAST(:source_refs AS jsonb), :rationale,
                      CAST(:result AS jsonb), :confidence, :human_review_required
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "sequence_no": sequence_no,
                    "step_type": step_type,
                    "question": question,
                    "input_refs": _json_text(
                        [{"project_id": preview["project_id"]}]
                    ),
                    "rule_refs": _json_text(
                        [{"route_code": preview["route_code"]}]
                    ),
                    "source_refs": _json_text(source_refs),
                    "rationale": (
                        "数据库规则、显式税率选择和保存的企业事实形成的"
                        "确定性业务说明；不保存模型隐藏思维过程。"
                    ),
                    "result": _json_text(result),
                    "confidence": (
                        Decimal("0.95")
                        if preview["status"] == "COMPLETE"
                        else Decimal("0.80")
                    ),
                    "human_review_required": preview["status"] != "COMPLETE",
                },
            )

    def _insert_missing(
        self, *, run_id: UUID, items: list[dict[str, Any]]
    ) -> None:
        for item in items:
            self._session.execute(
                text(
                    """
                    INSERT INTO audit.missing_data (
                      missing_data_id, calculation_run_id, field_path,
                      description, data_owner, data_kind, data_ownership,
                      blocking_scope, priority, next_action, status
                    ) VALUES (
                      :id, :run_id, :field_path, :description, :data_owner,
                      CAST(:data_kind AS ref.missing_data_kind),
                      CAST(:data_ownership AS ref.data_ownership),
                      :blocking_scope, CAST(:priority AS ref.priority),
                      :next_action, 'OPEN'
                    )
                    """
                ),
                {"id": uuid4(), "run_id": run_id, **item},
            )

    def _insert_llm_view(
        self,
        *,
        run_id: UUID,
        scenario_model_id: UUID,
        snapshot_id: UUID,
        preview: dict[str, Any],
    ) -> None:
        rows = (
            ("SCENARIO_MODEL", scenario_model_id, {"route_code": preview["route_code"], "calculation_scope": preview["calculation_scope"]}, "解释路径和公式范围。"),
            ("CALCULATION_RUN", run_id, {"status": preview["status"], "totals": preview["totals"], "warnings": preview["warnings"]}, "解释已保存的确定性计算结果。"),
            ("INPUT_SNAPSHOT", snapshot_id, {"project_id": preview["project_id"], "operational_use_permitted": preview["operational_use_permitted"]}, "解释输入快照和使用限制。"),
        )
        for sequence_no, (record_type, record_id, fields, why_read) in enumerate(rows, 1):
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
                      CAST(:data_quality AS ref.verification_status), true
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "sequence_no": sequence_no,
                    "record_type": record_type,
                    "record_id": record_id,
                    "fields": _json_text(fields),
                    "why_read": why_read,
                    "data_quality": (
                        "VERIFIED"
                        if preview["status"] == "COMPLETE"
                        else "CANDIDATE"
                    ),
                },
            )

    def _scenario_model_id(self, route_code: str) -> UUID:
        value = self._session.execute(
            text(
                """
                SELECT scenario_model_id
                FROM rules.tax_scenario_model
                WHERE classification_route = :route_code
                  AND record_status = 'ACTIVE'
                ORDER BY version DESC
                LIMIT 1
                """
            ),
            {"route_code": route_code},
        ).scalar_one_or_none()
        if value is None:
            raise ValueError(f"No active scenario model for {route_code}")
        return value

    def _country_id(self, iso2: str) -> UUID:
        value = self._session.execute(
            text("SELECT country_id FROM ref.country WHERE iso2 = :iso2"),
            {"iso2": iso2},
        ).scalar_one_or_none()
        if value is None:
            raise ValueError(f"Country {iso2} not found")
        return value

    def _rule_id(self, rule_code: str) -> UUID:
        value = self._session.execute(
            text(
                """
                SELECT rule_card_id
                FROM rules.country_rule_card
                WHERE rule_code = :rule_code AND record_status = 'ACTIVE'
                ORDER BY version DESC LIMIT 1
                """
            ),
            {"rule_code": rule_code},
        ).scalar_one()
        return value

    def _route_name(self, route_code: str | None) -> str | None:
        if route_code is None:
            return None
        return self._session.execute(
            text(
                """
                SELECT route_name_cn
                FROM rules.vehicle_tax_route
                WHERE route_code = :route_code AND record_status = 'ACTIVE'
                ORDER BY version DESC LIMIT 1
                """
            ),
            {"route_code": route_code},
        ).scalar_one_or_none()

    def _route_import_mode(self, route_code: str) -> str:
        return self._session.execute(
            text(
                """
                SELECT import_mode::text
                FROM rules.vehicle_tax_route
                WHERE route_code = :route_code AND record_status = 'ACTIVE'
                ORDER BY version DESC LIMIT 1
                """
            ),
            {"route_code": route_code},
        ).scalar_one()
