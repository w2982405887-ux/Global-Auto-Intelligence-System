from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.vietnam_quick_estimate import VietnamQuickEstimateService


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


class QuickEstimateService:
    """Four-condition, non-blocking statutory and incentive scenario estimate."""

    ROUTES = {
        "CBU": "ROUTE-MY-01-CBU",
        "CKD": "ROUTE-MY-02-CKD-WHOLE-KIT",
    }

    def __init__(self, session: Session) -> None:
        self._session = session

    def estimate(
        self,
        *,
        country_iso2: str,
        origin_country_iso2: str,
        effective_date: date,
        path: str,
        powertrain: str,
        cbu_tariff_code: str | None,
        ckd_declaration_mode: str,
        ckd_tariff_code: str | None,
        customs_value_cbu: Decimal | None,
        customs_value_ckd: Decimal | None,
        ckd_component_tariff_codes: dict[str, str],
    ) -> dict[str, Any]:
        country_iso2 = country_iso2.upper()
        if country_iso2 == "VN":
            return VietnamQuickEstimateService(self._session).estimate(
                origin_country_iso2=origin_country_iso2,
                effective_date=effective_date,
                path=path,
                powertrain=powertrain,
                cbu_tariff_code=cbu_tariff_code,
                ckd_declaration_mode=ckd_declaration_mode,
                customs_value_cbu=customs_value_cbu,
                customs_value_ckd=customs_value_ckd,
                ckd_component_tariff_codes=ckd_component_tariff_codes,
            )
        if country_iso2 != "MY":
            raise ValueError("快速测算目前支持马来西亚和越南")
        selected_paths = ("CBU", "CKD") if path == "AUTO" else (path,)
        required_code_missing = (
            ("CBU" in selected_paths and not cbu_tariff_code)
            or (
                "CKD" in selected_paths
                and ckd_declaration_mode == "WHOLE_KIT"
                and not ckd_tariff_code
            )
        )
        if required_code_missing:
            raise ValueError("请先填写所选路径对应的6至10位税号")
        results = [
            self._estimate_path(
                route_key=route_key,
                effective_date=effective_date,
                powertrain=powertrain,
                selected_tariff_code=(
                    cbu_tariff_code if route_key == "CBU" else ckd_tariff_code
                ),
                origin_country_iso2=origin_country_iso2,
                ckd_declaration_mode=ckd_declaration_mode,
                customs_value=(
                    customs_value_cbu if route_key == "CBU" else customs_value_ckd
                ),
            )
            for route_key in selected_paths
        ]
        comparable = [
            item
            for item in results
            if item["statutory"]["effective_tax_rate"] is not None
        ]
        recommended = (
            min(
                comparable,
                key=lambda item: Decimal(str(item["statutory"]["effective_tax_rate"])),
            )["path"]
            if comparable
            else None
        )
        advantage = None
        if len(comparable) == 2:
            rates = {
                item["path"]: Decimal(
                    str(item["statutory"]["effective_tax_rate"])
                )
                for item in comparable
            }
            advantage = abs(rates["CBU"] - rates["CKD"])
        return {
            "country_iso2": country_iso2,
            "country_name_cn": "马来西亚",
            "origin_country_iso2": origin_country_iso2.upper(),
            "effective_date": effective_date,
            "powertrain": powertrain,
            "requested_path": path,
            "estimate_level": (
                "ENTERPRISE_ESTIMATE"
                if customs_value_cbu is not None or customs_value_ckd is not None
                else "QUICK_ESTIMATE"
            ),
            "recommendation": {
                "recommended_path": recommended,
                "statutory_rate_advantage": advantage,
                "confidence": self._comparison_confidence(results),
                "summary": self._summary(recommended, results),
                "largest_uncertainty": (
                    "CKD本地成车消费税、销售税及项目优惠资格"
                    if any(item["path"] == "CKD" for item in results)
                    else "最终十位税号和车型法定消费税率"
                ),
            },
            "paths": results,
            "assumptions": [
                {
                    "condition": "车型细分",
                    "treatment": (
                        "系统未默认任何车身类型或具体十位税号；"
                        "需补充用途、车身、座位数和装运状态后再归类"
                    ),
                    "kind": "SYSTEM_DEFAULT",
                },
                {
                    "condition": "FTA资格",
                    "treatment": (
                        f"原产国为{origin_country_iso2.upper()}；法定场景暂按MFN，"
                        "优惠税率必须结合协定、原产地规则和证明文件确认"
                    ),
                    "kind": "PREFERENCE_ASSUMPTION",
                },
                {
                    "condition": "计税价值",
                    "treatment": (
                        "未填写企业金额时使用标准化税基100，只输出有效税率"
                    ),
                    "kind": "STANDARDIZED_BASE",
                },
                {
                    "condition": "审批与项目优惠",
                    "treatment": "不阻塞法定测算；只影响优惠情景是否可落地",
                    "kind": "NON_BLOCKING",
                },
            ],
            "disclaimer": (
                "公开规则快速估算，不构成正式归类、报关或税务意见。"
                "最终结果仍需企业税号、计税价值及审批文件确认。"
            ),
        }

    def _estimate_path(
        self,
        *,
        route_key: str,
        effective_date: date,
        powertrain: str,
        selected_tariff_code: str | None,
        origin_country_iso2: str,
        ckd_declaration_mode: str,
        customs_value: Decimal | None,
    ) -> dict[str, Any]:
        route_code = self.ROUTES[route_key]
        if route_key == "CKD" and ckd_declaration_mode == "PARTS_BOM":
            rows: list[dict[str, Any]] = []
        else:
            rows = self._selected_tariff_rows(
                route_code=route_code,
                effective_date=effective_date,
                powertrain=powertrain,
                selected_tariff_code=selected_tariff_code,
                origin_country_iso2=origin_country_iso2,
            )
        if not rows:
            return {
                "path": route_key,
                "route_code": route_code,
                "status": "SCENARIO_MATCHED_CLASSIFICATION_PENDING",
                "confidence": "MEDIUM",
                "classification_scope": {
                    "status": (
                        "USER_SELECTED_PENDING_VERIFICATION"
                        if selected_tariff_code
                        else "PARTS_BOM_REQUIRED"
                    ),
                    "candidate_scope": (
                        "CBU乘用车辆税目范围"
                        if route_key == "CBU"
                        else (
                            "CKD零件BOM多税号申报"
                            if ckd_declaration_mode == "PARTS_BOM"
                            else "CKD整套税号申报"
                        )
                    ),
                    "final_national_tariff_code": selected_tariff_code,
                    "required_facts": [
                        "车辆用途与车身类型",
                        "座位数及车辆类别",
                        "装运时完整或拆解状态",
                        "CKD关键部件连接与装配状态"
                        if route_key == "CKD"
                        else "完整车辆技术参数",
                    ],
                },
                "candidate_tariffs": [],
                "statutory": self._empty_scenario("MFN法定场景"),
                "incentive": self._empty_scenario("优惠对比场景"),
                "missing_items": [
                    (
                        "数据库中未找到与所选税号、日期、路径和动力类型完全匹配的有效记录"
                        if selected_tariff_code
                        else "需要上传BOM并逐项选择零件税号"
                    ),
                ],
                "dependency_level": "HIGH" if route_key == "CKD" else "MEDIUM",
                "recommended_use": (
                    "长期本地化与规模化经营"
                    if route_key == "CKD"
                    else "短期快速进入市场"
                ),
            }
        mfn = next((row for row in rows if row["regime"] == "MFN"), None)
        fta_rows = [row for row in rows if row["regime"] != "MFN"]
        base = customs_value or Decimal("100")
        statutory = self._calculate(
            row=mfn, base=base, route_key=route_key, name="MFN法定场景"
        )
        incentive_candidates = [
            self._calculate(
                row=row,
                base=base,
                route_key=route_key,
                name=f"{row['regime']}优惠场景",
            )
            for row in fta_rows
        ]
        incentive_candidates = [
            item
            for item in incentive_candidates
            if item["effective_tax_rate"] is not None
        ]
        incentive = (
            min(
                incentive_candidates,
                key=lambda item: Decimal(str(item["effective_tax_rate"])),
            )
            if incentive_candidates
            else self._empty_scenario("优惠对比场景")
        )
        missing = list(statutory["unknown_tax_items"])
        if route_key == "CKD":
            missing.extend(
                [
                    "本地成车法定消费税率或已批准豁免",
                    "本地成车销售税率或已批准豁免",
                ]
            )
        confidence = (
            "MEDIUM"
            if mfn and mfn["verification_status"] in ("VERIFIED", "RULING_CONFIRMED")
            else "LOW"
        )
        return {
            "path": route_key,
            "route_code": route_code,
            "status": "ESTIMATED" if statutory["effective_tax_rate"] is not None else "PARTIAL",
            "confidence": confidence,
            "matched_tariff": (
                {
                    "national_tariff_code": mfn["national_tariff_code"],
                    "hs6_code": mfn["hs6_code"],
                    "description": mfn["tariff_description"],
                    "verification_status": mfn["verification_status"],
                    "source_code": mfn["source_code"],
                    "source_locator": mfn["source_locator"],
                }
                if mfn
                else None
            ),
            "candidate_tariffs": [
                {
                    "regime": row["regime"],
                    "national_tariff_code": row["national_tariff_code"],
                    "import_duty_rate": row["import_duty_rate"],
                    "excise_duty_rate": row["excise_duty_rate"],
                    "sales_tax_rate": row["sales_tax_rate"],
                    "verification_status": row["verification_status"],
                }
                for row in rows
            ],
            "statutory": statutory,
            "incentive": incentive,
            "missing_items": list(dict.fromkeys(missing)),
            "dependency_level": "HIGH" if route_key == "CKD" else "LOW",
            "recommended_use": (
                "长期本地化与规模化经营" if route_key == "CKD" else "短期快速进入市场"
            ),
        }

    def _selected_tariff_rows(
        self,
        *,
        route_code: str,
        effective_date: date,
        powertrain: str,
        selected_tariff_code: str | None,
        origin_country_iso2: str,
    ) -> list[dict[str, Any]]:
        if not selected_tariff_code:
            return []
        result = self._session.execute(
            text(
                """
                SELECT
                  CASE
                    WHEN line.origin_regime::text = 'MFN' THEN 'MFN'
                    ELSE agreement.agreement_code
                  END AS regime,
                  line.origin_regime::text AS origin_regime,
                  agreement.agreement_code,
                  line.hs6_code,
                  line.national_tariff_code,
                  line.tariff_description,
                  line.import_duty_rate,
                  line.sales_tax_rate,
                  line.excise_duty_rate,
                  line.verification_status::text AS verification_status,
                  source.source_code,
                  clause.locator_value AS source_locator
                FROM customs.vehicle_tariff_rate_line line
                JOIN rules.vehicle_tax_route route
                  ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
                LEFT JOIN ref.trade_agreement agreement
                  ON agreement.trade_agreement_id = line.trade_agreement_id
                JOIN evidence.source_clause clause
                  ON clause.source_clause_id = line.tariff_source_clause_id
                JOIN evidence.source_document source
                  ON source.source_document_id = clause.source_document_id
                WHERE route.route_code = :route_code
                  AND line.record_status = 'ACTIVE'
                  AND line.effective_from <= :effective_date
                  AND (line.effective_to IS NULL OR line.effective_to > :effective_date)
                  AND line.powertrain::text = :powertrain
                  AND line.national_tariff_code = :selected_tariff_code
                  AND (
                    line.origin_regime::text = 'MFN'
                    OR line.eligibility_condition->>'origin_country_iso2'
                       = :origin_country_iso2
                  )
                ORDER BY
                  CASE WHEN line.origin_regime::text = 'MFN' THEN 0 ELSE 1 END,
                  agreement.agreement_code
                """
            ),
            {
                "route_code": route_code,
                "effective_date": effective_date,
                "powertrain": powertrain,
                "selected_tariff_code": selected_tariff_code,
                "origin_country_iso2": origin_country_iso2.upper(),
            },
        )
        return [dict(row._mapping) for row in result]

    def _calculate(
        self,
        *,
        row: dict[str, Any] | None,
        base: Decimal,
        route_key: str,
        name: str,
    ) -> dict[str, Any]:
        if row is None:
            return self._empty_scenario(name)
        duty_rate = (
            Decimal(str(row["import_duty_rate"]))
            if row["import_duty_rate"] is not None
            else None
        )
        excise_rate = (
            Decimal(str(row["excise_duty_rate"]))
            if row["excise_duty_rate"] is not None
            else None
        )
        sst_rate = (
            Decimal(str(row["sales_tax_rate"]))
            if row["sales_tax_rate"] is not None
            else None
        )
        unknown: list[str] = []
        if duty_rate is None:
            unknown.append("进口关税")
        if route_key == "CBU" and excise_rate is None:
            unknown.append("消费税")
        if sst_rate is None:
            unknown.append("销售税")
        duty = _money(base * duty_rate) if duty_rate is not None else Decimal("0")
        excise_base = _money(base + duty)
        excise = (
            _money(excise_base * excise_rate)
            if route_key == "CBU" and excise_rate is not None
            else Decimal("0")
        )
        sst_base = _money(base + duty + excise)
        sst = _money(sst_base * sst_rate) if sst_rate is not None else Decimal("0")
        known_tax = _money(duty + excise + sst)
        effective = _rate(known_tax / base) if not unknown and base > 0 else None
        return {
            "name": name,
            "regime": row["regime"],
            "base_value": base,
            "import_duty_rate": duty_rate,
            "excise_duty_rate": excise_rate,
            "sales_tax_rate": sst_rate,
            "known_tax_amount": known_tax,
            "effective_tax_rate": effective,
            "tax_lines": [
                {
                    "tax": "IMPORT_DUTY",
                    "base": base,
                    "rate": duty_rate,
                    "amount": duty,
                    "formula": "海关价值 × 进口关税率",
                },
                {
                    "tax": "EXCISE",
                    "base": excise_base,
                    "rate": excise_rate,
                    "amount": excise if route_key == "CBU" else None,
                    "formula": "（海关价值＋进口关税）× 消费税率",
                    "scope_note": "CKD本地成车阶段另行计算" if route_key == "CKD" else None,
                },
                {
                    "tax": "SST",
                    "base": sst_base,
                    "rate": sst_rate,
                    "amount": sst,
                    "formula": "（海关价值＋进口关税＋消费税）× 销售税率",
                },
            ],
            "unknown_tax_items": unknown,
            "is_complete_statutory_chain": not unknown and route_key == "CBU",
        }

    @staticmethod
    def _empty_scenario(name: str) -> dict[str, Any]:
        return {
            "name": name,
            "regime": None,
            "base_value": None,
            "known_tax_amount": None,
            "effective_tax_rate": None,
            "tax_lines": [],
            "unknown_tax_items": ["缺少适用税率数据"],
            "is_complete_statutory_chain": False,
        }

    @staticmethod
    def _comparison_confidence(results: list[dict[str, Any]]) -> str:
        if not results or any(item["confidence"] == "LOW" for item in results):
            return "LOW"
        if any(item["path"] == "CKD" for item in results):
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _summary(recommended: str | None, results: list[dict[str, Any]]) -> str:
        if recommended == "CKD":
            return (
                "当前公开法定进口环节显示CKD潜在税负较低，但优势依赖本地组装、"
                "本地成车税负和项目优惠资格；CBU更适合短期快速进入。"
            )
        if recommended == "CBU":
            return "当前公开法定场景下CBU已知税负更低，建议优先核实CKD项目优惠后再决策。"
        if len(results) == 1:
            return "已生成所选路径的公开规则快速估算，请结合下方假设和缺失项使用。"
        return "当前公开数据不足以形成可靠排名，系统保留未知税项而未生成虚假税率。"
