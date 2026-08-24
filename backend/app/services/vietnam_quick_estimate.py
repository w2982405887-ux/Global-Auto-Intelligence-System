from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


ASEAN = {"BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "VN"}
RCEP = ASEAN | {"AU", "CN", "JP", "KR", "NZ"}
DEFAULT_WEIGHTS = {
    "VN-CKD-TRACTION-BATTERY": Decimal("0.25"),
    "VN-CKD-TRACTION-MOTOR": Decimal("0.08"),
    "VN-CKD-E-POWER-CONTROL": Decimal("0.07"),
    "VN-CKD-GASOLINE-ENGINE": Decimal("0.12"),
    "VN-CKD-DIESEL-ENGINE": Decimal("0.12"),
    "VN-CKD-TRANSMISSION-REDUCER": Decimal("0.10"),
    "VN-CKD-BODY": Decimal("0.18"),
    "VN-CKD-CHASSIS": Decimal("0.07"),
    "VN-CKD-SUSPENSION-AXLE": Decimal("0.05"),
    "VN-CKD-STEERING": Decimal("0.02"),
    "VN-CKD-BRAKING": Decimal("0.03"),
    "VN-CKD-TYRE-WHEEL": Decimal("0.03"),
    "VN-CKD-THERMAL": Decimal("0.03"),
    "VN-CKD-WIRING-HARNESS": Decimal("0.02"),
    "VN-CKD-SEATS": Decimal("0.02"),
    "VN-CKD-GLASS": Decimal("0.01"),
    "VN-CKD-LIGHTING": Decimal("0.01"),
    "VN-CKD-INSTRUMENT-DISPLAY": Decimal("0.01"),
    "VN-CKD-SAFETY": Decimal("0.01"),
}


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def dec(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def agreement_applies(agreement: str | None, origin: str) -> bool:
    origin = origin.upper()
    if agreement == "ACFTA":
        return origin == "CN" or origin in ASEAN
    if agreement == "ATIGA":
        return origin in ASEAN
    if agreement == "RCEP":
        return origin in RCEP
    return False


def origin_group(agreement: str, origin: str) -> str | None:
    origin = origin.upper()
    if agreement == "ACFTA":
        return "CN" if origin == "CN" else ("ASEAN" if origin in ASEAN else None)
    if agreement == "ATIGA":
        return "ASEAN" if origin in ASEAN else None
    if agreement == "RCEP":
        return "ASEAN" if origin in ASEAN else (origin if origin in {"CN", "AU", "JP", "KR", "NZ"} else None)
    return None


class VietnamQuickEstimateService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def estimate(
        self,
        *,
        origin_country_iso2: str,
        effective_date: date,
        path: str,
        powertrain: str,
        cbu_tariff_code: str | None,
        ckd_declaration_mode: str,
        customs_value_cbu: Decimal | None,
        customs_value_ckd: Decimal | None,
        ckd_component_tariff_codes: dict[str, str],
    ) -> dict[str, Any]:
        paths = ("CBU", "CKD") if path == "AUTO" else (path,)
        if "CBU" in paths and not cbu_tariff_code:
            raise ValueError("越南CBU测算需要先选择整车10位税号")
        policies = self.policy_matches(origin_country_iso2, effective_date, powertrain, paths)
        results = []
        if "CBU" in paths:
            results.append(self.cbu(origin_country_iso2, effective_date, powertrain, cbu_tariff_code or "", customs_value_cbu, policies))
        if "CKD" in paths:
            results.append(self.ckd(
                origin_country_iso2,
                effective_date,
                powertrain,
                ckd_declaration_mode,
                customs_value_ckd,
                policies,
                ckd_component_tariff_codes,
            ))
        comparable = [x for x in results if x["statutory"]["effective_tax_rate"] is not None]
        recommended = min(comparable, key=lambda x: Decimal(str(x["statutory"]["effective_tax_rate"])))["path"] if comparable else None
        advantage = None
        if len(comparable) == 2:
            a = {x["path"]: Decimal(str(x["statutory"]["effective_tax_rate"])) for x in comparable}
            advantage = abs(a["CBU"] - a["CKD"])
        return {
            "country_iso2": "VN",
            "country_name_cn": "越南",
            "origin_country_iso2": origin_country_iso2.upper(),
            "effective_date": effective_date,
            "powertrain": powertrain,
            "requested_path": path,
            "estimate_level": "ENTERPRISE_ESTIMATE" if customs_value_cbu or customs_value_ckd else "QUICK_ESTIMATE",
            "recommendation": {
                "recommended_path": recommended,
                "statutory_rate_advantage": advantage,
                "confidence": "LOW" if any(x["confidence"] == "LOW" for x in results) else "MEDIUM",
                "summary": "CBU可计算整车进口税链；CKD当前可估主要零件进口阶段，并已匹配FTA、BEV低SCT、98.49等特殊政策。",
                "largest_uncertainty": "CKD本地组装后SCT/VAT、98.49资格、BOM价值占比",
            },
            "paths": results,
            "policy_matches": policies,
            "assumptions": [
                {"condition": "业务范围", "treatment": "仅限越南新车、乘用车；二手车、商用车、两轮车排除。", "kind": "SCOPE"},
                {"condition": "FTA资格", "treatment": "原产国决定可选协定，实际适用仍需原产规则、直运和原产证明。", "kind": "PREFERENCE"},
                {"condition": "CKD阶段", "treatment": "当前只估主要零件进口阶段；本地成车SCT/VAT后续补充。", "kind": "PARTIAL"},
                {"condition": "特殊政策", "treatment": "FTA、BEV低SCT、登记费、98.49、NEV产量门槛均已逐项匹配并标注状态。", "kind": "INCENTIVE_MATCH"},
            ],
            "disclaimer": "公开规则快速估算，不构成正式归类、报关或税务意见。",
        }

    def cbu(self, origin: str, as_of: date, powertrain: str, code: str, value: Decimal | None, policies: list[dict[str, Any]]) -> dict[str, Any]:
        rows = self.cbu_rows(as_of, powertrain, code)
        mfn = next((r for r in rows if r["regime"] == "MFN"), None)
        ftas = [r for r in rows if r["regime"] != "MFN" and agreement_applies(r["agreement_code"], origin)]
        base = value or Decimal("100")
        statutory = self.vehicle_chain(mfn, base, "MFN法定场景")
        candidates = [self.vehicle_chain(r, base, f"{r['regime']}优惠场景") for r in ftas]
        candidates = [x for x in candidates if x["effective_tax_rate"] is not None]
        incentive = min(candidates, key=lambda x: Decimal(str(x["effective_tax_rate"]))) if candidates else self.empty("优惠对比场景")
        missing = list(statutory["unknown_tax_items"])
        if not ftas:
            missing.append("当前原产国未匹配到可用FTA整车税率")
        return {
            "path": "CBU",
            "route_code": "ROUTE-VN-01-CBU-NEW-PASSENGER",
            "status": "ESTIMATED" if statutory["effective_tax_rate"] is not None else "PARTIAL",
            "confidence": "MEDIUM" if rows else "LOW",
            "matched_tariff": {
                "national_tariff_code": mfn["national_tariff_code"],
                "hs6_code": mfn["hs6_code"],
                "description": mfn["tariff_description"],
                "verification_status": mfn["verification_status"],
                "source_code": mfn["source_code"],
                "source_locator": mfn["source_locator"],
            } if mfn else None,
            "candidate_tariffs": [{"regime": r["regime"], "national_tariff_code": r["national_tariff_code"], "import_duty_rate": r["import_duty_rate"], "excise_duty_rate": r["excise_duty_rate"], "sales_tax_rate": r["sales_tax_rate"], "verification_status": r["verification_status"]} for r in ([x for x in rows if x["regime"] == "MFN"] + ftas)],
            "statutory": statutory,
            "incentive": incentive,
            "policy_matches": [p for p in policies if "CBU" in p["applies_to_paths"] or p["match_status"] == "INFORMATION_ONLY"],
            "missing_items": list(dict.fromkeys(missing)),
            "dependency_level": "MEDIUM",
            "recommended_use": "短期快速进入市场",
        }

    def ckd(
        self,
        origin: str,
        as_of: date,
        powertrain: str,
        mode: str,
        value: Decimal | None,
        policies: list[dict[str, Any]],
        selected_codes: dict[str, str],
    ) -> dict[str, Any]:
        base = value or Decimal("100")
        candidate_components = self.ckd_component_candidates(origin, as_of, powertrain)
        # MFN is the statutory baseline and must be queried from the same
        # component mapping table as the preferential regimes.  The previous
        # implementation hard-coded MFN as "not ingested", which made a
        # newly seeded ordinary tariff row invisible to the CKD service.
        statutory = self.ckd_agreement("MFN", origin, as_of, powertrain, base, selected_codes)
        all_estimates = [
            self.ckd_agreement(a, origin, as_of, powertrain, base, selected_codes)
            for a in ("ACFTA", "ATIGA", "RCEP")
            if agreement_applies(a, origin)
        ]
        estimates = [x for x in all_estimates if x["effective_tax_rate"] is not None]
        complete_estimates = [x for x in estimates if not x.get("unknown_tax_items")]
        if complete_estimates:
            incentive = min(complete_estimates, key=lambda x: Decimal(str(x["effective_tax_rate"])))
        elif estimates:
            incentive = min(
                estimates,
                key=lambda x: (
                    -int(x.get("matched_component_count", 0)),
                    Decimal(str(x["effective_tax_rate"])),
                ),
            )
        elif all_estimates:
            # Keep the detailed missing-item list visible when no agreement can
            # yet be calculated.  Do not collapse it into a generic empty result.
            incentive = max(
                all_estimates,
                key=lambda x: int(x.get("matched_component_count", 0)),
            )
        else:
            incentive = self.empty("零件FTA进口阶段估算")
        # Keep the distinction between a missing database row and a missing
        # user classification/selection.  A candidate row is useful evidence
        # but does not become a final tariff selection automatically.
        missing_items = ["企业BOM价值占比", "进口VAT", "本地组装后SCT", "本地组装后VAT", "98.49资格"]
        mfn_components = {
            str(group.get("ccu_code"))
            for group in candidate_components
            if any(str(candidate.get("regime") or candidate.get("agreement") or "").upper() == "MFN"
                   for candidate in group.get("candidates") or [])
        }
        if len(mfn_components) < len(self.weights(powertrain)):
            missing_items.insert(0, "主要零件MFN税率")
        missing_items.extend(incentive.get("unknown_tax_items", []))
        tax_chain = self.ckd_tax_chain(
            origin=origin,
            powertrain=powertrain,
            mode=mode,
            base=base,
            import_scenario=incentive,
        )
        return {
            "path": "CKD",
            "route_code": "ROUTE-VN-CKD-PARTS-MAJOR-ESTIMATE",
            "status": "PARTIAL_IMPORT_STAGE_ESTIMATED" if incentive["effective_tax_rate"] is not None else "CLASSIFICATION_SELECTION_REQUIRED",
            "confidence": "LOW",
            "classification_scope": {"status": "MAJOR_COMPONENT_TARIFF_SELECTION_REQUIRED", "candidate_scope": "CKD主要零件多税号估算", "final_national_tariff_code": None, "required_facts": ["BOM逐项HS/VN税号", "每个零件的技术状态和用途", "每个零件原产国", "各零件海关价值占比", "GRI 2(a)风险审查"]},
            "candidate_tariffs": [{"regime": x.get("regime") or "FTA", "national_tariff_code": "MULTI-HS-MAJOR-PARTS", "import_duty_rate": x.get("import_duty_rate"), "excise_duty_rate": None, "sales_tax_rate": "0.10", "verification_status": "CANDIDATE"} for x in all_estimates],
            "statutory": statutory,
            "incentive": incentive,
            "component_candidates": candidate_components,
            "policy_matches": [p for p in policies if "CKD" in p["applies_to_paths"] or p["match_status"] == "INFORMATION_ONLY"],
            "missing_items": list(dict.fromkeys(missing_items)),
            "tax_chain": tax_chain,
            "dependency_level": "HIGH",
            "recommended_use": "长期本地化与规模化经营",
        }

    @staticmethod
    def ckd_tax_chain(
        *,
        origin: str,
        powertrain: str,
        mode: str,
        base: Decimal,
        import_scenario: dict[str, Any],
    ) -> dict[str, Any]:
        """Return an auditable four-stage CKD tax chain.

        The current Vietnam CKD estimator only has enough data for a weighted
        major-parts import-duty estimate.  This method deliberately keeps all
        other stages explicit and unknown instead of treating missing taxes as
        zero.  It is a response contract, not a new tax-law assumption.
        """
        known_import_amount = dec(import_scenario.get("known_tax_amount"))
        known_import_amount = money(known_import_amount) if known_import_amount is not None else None
        known_import_rate = None
        if known_import_amount is not None and base:
            known_import_rate = rate(known_import_amount / base)
        import_rate = dec(import_scenario.get("import_duty_rate"))
        import_lines = import_scenario.get("tax_lines") or []
        import_status = "KNOWN_PARTIAL" if known_import_amount is not None else "BLOCKED"
        import_missing = [
            "进口VAT税率与进口计税基础",
            "进口VAT进项抵扣资格/时点",
        ]
        if not import_scenario.get("unknown_tax_items") and import_rate is not None:
            import_status = "PARTIAL"

        return {
            "version": "VN-CKD-FULL-CHAIN-2026-08",
            "status": "PARTIAL",
            "classification_route": mode,
            "powertrain": powertrain,
            "base_value": base,
            "known_tax_amount": known_import_amount,
            "known_effective_rate": known_import_rate,
            "cash_tax_outlay": None,
            "non_recoverable_tax_rate": None,
            "unknown_tax_items": list(dict.fromkeys([
                "出口环节企业出口增值税/退税口径",
                *import_missing,
                "本地组装后SCT的车辆类别、座位数、排量和计税价格",
                "本地组装资格及SCT优惠资格",
                "本地组装后VAT计税价格与进项抵扣",
                "越南终端销售价格及销售VAT处理",
            ])),
            "assumptions": [
                "当前只把已确认主要零件税号产生的进口关税计入已知税额。",
                "未建模税种不按0%处理；补齐计税基础和资格后才能计算现金税负。",
                "标准化基数仅用于加权估算，不代表企业实际单车CIF。",
            ],
            "nodes": [
                {
                    "stage_code": "EXPORT",
                    "stage_name": f"{origin.upper()}出口",
                    "status": "NOT_MODELED",
                    "known_tax_amount": None,
                    "known_effective_rate": None,
                    "recoverability": "OUT_OF_SCOPE",
                    "tax_lines": [],
                    "missing_fields": ["出口主体、出口VAT处理、出口退税率和退税资格"],
                    "note": "出口环节不纳入当前越南CKD进口关税估算；不得默认退税或出口税为0。",
                },
                {
                    "stage_code": "VN_IMPORT",
                    "stage_name": "越南进口",
                    "status": import_status,
                    "known_tax_amount": known_import_amount,
                    "known_effective_rate": known_import_rate,
                    "recoverability": "VAT_POTENTIALLY_CREDITABLE",
                    "tax_lines": [
                        *import_lines,
                        {
                            "tax": "IMPORT_VAT",
                            "base": None,
                            "rate": None,
                            "amount": None,
                            "formula": "待补充进口VAT法定税基与税率",
                            "status": "NOT_MODELED",
                        },
                    ],
                    "missing_fields": import_missing,
                    "note": f"已知进口关税率：{known_import_rate if known_import_rate is not None else '待确认'}；进口VAT未计入。",
                },
                {
                    "stage_code": "VN_ASSEMBLY",
                    "stage_name": "越南本地组装",
                    "status": "NOT_MODELED",
                    "known_tax_amount": None,
                    "known_effective_rate": None,
                    "recoverability": "NOT_APPLICABLE",
                    "tax_lines": [
                        {"tax": "LOCAL_SCT", "base": None, "rate": None, "amount": None, "formula": "成车计税价格 × 适用SCT税率", "status": "NOT_MODELED"},
                        {"tax": "LOCAL_VAT", "base": None, "rate": None, "amount": None, "formula": "组装后销售/应税价格 × VAT税率", "status": "NOT_MODELED"},
                    ],
                    "missing_fields": [
                        "座位数和车辆车身类别",
                        "发动机排量（适用ICE/HEV/PHEV/EREV时）",
                        "成车SCT计税价格",
                        "本地组装资格及优惠资格",
                    ],
                    "note": "当前越南CKD页面尚未将本地组装后的SCT/VAT接入数值引擎。",
                },
                {
                    "stage_code": "VN_SALES",
                    "stage_name": "越南终端销售",
                    "status": "NOT_MODELED",
                    "known_tax_amount": None,
                    "known_effective_rate": None,
                    "recoverability": "OUT_OF_SCOPE",
                    "tax_lines": [
                        {"tax": "SALES_VAT", "base": None, "rate": None, "amount": None, "formula": "终端销售价格 × VAT税率", "status": "NOT_MODELED"},
                    ],
                    "missing_fields": ["终端销售价格、销售VAT销项/进项处理、其他终端税费"],
                    "note": "终端销售税负属于完整生命周期测算，不在本轮进口关税结果中虚构。",
                },
            ],
        }

    def cbu_rows(self, as_of: date, powertrain: str, code: str) -> list[dict[str, Any]]:
        rows = self.session.execute(text("""
            SELECT CASE WHEN l.origin_regime::text='MFN' THEN 'MFN' ELSE a.agreement_code END regime,
                   a.agreement_code, l.hs6_code, l.national_tariff_code, l.tariff_description,
                   l.import_duty_rate, l.excise_duty_rate, l.sales_tax_rate,
                   l.verification_status::text verification_status, d.source_code, c.locator_value source_locator
            FROM customs.vehicle_tariff_rate_line l
            JOIN ref.country n ON n.country_id=l.country_id
            JOIN rules.vehicle_tax_route r ON r.vehicle_tax_route_id=l.vehicle_tax_route_id
            LEFT JOIN ref.trade_agreement a ON a.trade_agreement_id=l.trade_agreement_id
            JOIN evidence.source_clause c ON c.source_clause_id=l.tariff_source_clause_id
            JOIN evidence.source_document d ON d.source_document_id=c.source_document_id
            WHERE n.iso2='VN' AND r.route_code='ROUTE-VN-01-CBU-NEW-PASSENGER'
              AND l.record_status='ACTIVE' AND l.effective_from<=:as_of
              AND (l.effective_to IS NULL OR l.effective_to>:as_of)
              AND l.powertrain::text=:powertrain AND l.national_tariff_code=:code
            ORDER BY CASE WHEN l.origin_regime::text='MFN' THEN 0 ELSE 1 END
        """), {"as_of": as_of, "powertrain": powertrain, "code": code})
        return [dict(r._mapping) for r in rows]

    def ckd_agreement(
        self,
        agreement: str,
        origin: str,
        as_of: date,
        powertrain: str,
        base: Decimal,
        selected_codes: dict[str, str],
    ) -> dict[str, Any]:
        # Ordinary MFN mappings have no trade_agreement_id.  Preferential
        # mappings are stored as origin_regime=FTA and joined to the named
        # agreement.  Keeping the two predicates explicit avoids treating an
        # FTA row as an MFN fallback (or vice versa).
        regime = agreement.upper()
        group = origin_group(regime, origin) if regime != "MFN" else None
        if regime != "MFN" and group is None:
            return self.empty(f"{agreement}主要零件进口阶段估算")
        if regime == "MFN":
            query = """
                SELECT ccu.ccu_code, ccu.ccu_name_cn,
                       m.national_tariff_code, m.duty_rate,
                       m.tariff_description, m.eligibility_condition,
                       m.origin_regime::text AS origin_regime,
                       NULL::text AS agreement_code,
                       m.effective_from, m.effective_to,
                       m.verification_status::text AS verification_status,
                       d.source_code, d.document_title,
                       d.canonical_url AS official_url,
                       c.locator_value AS source_locator,
                       c.clause_code, c.evidence_summary
                FROM customs.tariff_mapping m
                JOIN ref.country n ON n.country_id=m.country_id
                JOIN customs.ccu_candidate_hs h ON h.candidate_id=m.candidate_id
                JOIN customs.customs_classification_unit ccu ON ccu.ccu_id=h.ccu_id
                LEFT JOIN evidence.source_clause c ON c.source_clause_id=m.source_clause_id
                LEFT JOIN evidence.source_document d ON d.source_document_id=c.source_document_id
                WHERE n.iso2='VN' AND m.origin_regime::text='MFN'
                  AND m.record_status='ACTIVE'
                  AND m.effective_from<=:as_of
                  AND (m.effective_to IS NULL OR m.effective_to>:as_of)
                ORDER BY ccu.ccu_code, m.national_tariff_code
            """
            params = {"as_of": as_of}
        else:
            query = """
                SELECT ccu.ccu_code, ccu.ccu_name_cn,
                       m.national_tariff_code, m.duty_rate,
                       m.tariff_description, m.eligibility_condition,
                       m.origin_regime::text AS origin_regime,
                       a.agreement_code,
                       m.effective_from, m.effective_to,
                       m.verification_status::text AS verification_status,
                       d.source_code, d.document_title,
                       d.canonical_url AS official_url,
                       c.locator_value AS source_locator,
                       c.clause_code, c.evidence_summary
                FROM customs.tariff_mapping m
                JOIN ref.country n ON n.country_id=m.country_id
                JOIN ref.trade_agreement a ON a.trade_agreement_id=m.trade_agreement_id
                JOIN customs.ccu_candidate_hs h ON h.candidate_id=m.candidate_id
                JOIN customs.customs_classification_unit ccu ON ccu.ccu_id=h.ccu_id
                LEFT JOIN evidence.source_clause c ON c.source_clause_id=m.source_clause_id
                LEFT JOIN evidence.source_document d ON d.source_document_id=c.source_document_id
                WHERE n.iso2='VN' AND m.origin_regime::text='FTA'
                  AND a.agreement_code=:agreement AND m.record_status='ACTIVE'
                  AND m.effective_from<=:as_of
                  AND (m.effective_to IS NULL OR m.effective_to>:as_of)
                  AND m.eligibility_condition->>'origin_group'=:group
                ORDER BY ccu.ccu_code, m.national_tariff_code
            """
            params = {"agreement": regime, "group": group, "as_of": as_of}
        rows = self.session.execute(text(query), params)
        by_ccu: dict[str, list[dict[str, Any]]] = {}
        for record in rows:
            item = dict(record._mapping)
            if self._is_candidate_eligible_for_origin(item, origin) and self._is_passenger_component_candidate(item):
                by_ccu.setdefault(item["ccu_code"], []).append(item)
        weights = self.weights(powertrain)
        duty = Decimal("0")
        lines = []
        missing = []
        for ccu, w in weights.items():
            chosen_code = selected_codes.get(ccu)
            if not chosen_code:
                missing.append(f"{ccu}尚未选择最终越南税号")
                continue
            row = next((item for item in by_ccu.get(ccu, []) if item["national_tariff_code"] == chosen_code), None)
            if not by_ccu.get(ccu):
                missing.append(f"{ccu}的{regime}普通税率行尚未入库")
                continue
            if not row or row["duty_rate"] is None:
                missing.append(f"{ccu}所选税号{chosen_code}不适用于{regime}/{origin.upper()}或当前日期")
                continue
            b = money(base * w)
            r = Decimal(str(row["duty_rate"]))
            amt = money(b * r)
            duty += amt
            lines.append({
                "tax": f"IMPORT_DUTY:{row['ccu_name_cn']}",
                "base": b,
                "rate": r,
                "amount": amt,
                "formula": f"{row['ccu_name_cn']}估算价值 × {regime}零件关税率",
                "scope_note": row["national_tariff_code"],
                "verification_status": row.get("verification_status"),
                "source_code": row.get("source_code"),
                "source_locator": row.get("source_locator"),
            })
        complete = not missing and len(lines) == len(weights)
        if not lines:
            result = self.empty(f"{regime}主要零件进口阶段估算")
            result["unknown_tax_items"] = missing or ["尚未选择任何最终越南税号"]
            result["matched_component_count"] = 0
            result["expected_component_count"] = len(weights)
            result["regime"] = regime
            return result
        return {
            "name": f"{regime}主要零件进口关税估算",
            "regime": regime,
            "base_value": base,
            "import_duty_rate": rate(duty / base) if complete else None,
            "excise_duty_rate": None,
            "sales_tax_rate": None,
            "known_tax_amount": duty,
            "effective_tax_rate": rate(duty / base) if complete else None,
            "tax_lines": lines,
            "unknown_tax_items": missing,
            "matched_component_count": len(lines),
            "expected_component_count": len(weights),
            "is_complete_statutory_chain": False,
        }

    def ckd_component_candidates(self, origin: str, as_of: date, powertrain: str) -> list[dict[str, Any]]:
        """Return candidates only.  No candidate is auto-selected by tax rate."""
        weights = self.weights(powertrain)
        rows: list[dict[str, Any]] = []
        # MFN is always returned as the baseline.  It is intentionally
        # separate from the FTA loop because MFN mappings have no agreement
        # foreign key and must not be hidden by a missing preference row.
        mfn_result = self.session.execute(text("""
            SELECT ccu.ccu_code, ccu.ccu_name_cn, ccu.required_input_fields,
                   ccu.technical_qualifiers,
                   m.national_tariff_code, m.tariff_description, m.duty_rate,
                   m.origin_regime::text AS origin_regime,
                   NULL::text AS agreement_code,
                   m.eligibility_condition,
                   m.effective_from, m.effective_to,
                   m.verification_status::text AS verification_status,
                   d.source_code, d.document_title,
                   d.canonical_url AS official_url,
                   c.locator_value AS source_locator,
                   c.clause_code, c.evidence_summary
            FROM customs.tariff_mapping m
            JOIN ref.country n ON n.country_id=m.country_id
            JOIN customs.ccu_candidate_hs h ON h.candidate_id=m.candidate_id
            JOIN customs.customs_classification_unit ccu ON ccu.ccu_id=h.ccu_id
            LEFT JOIN evidence.source_clause c ON c.source_clause_id=m.source_clause_id
            LEFT JOIN evidence.source_document d ON d.source_document_id=c.source_document_id
            WHERE n.iso2='VN' AND m.origin_regime::text='MFN'
              AND m.record_status='ACTIVE'
              AND m.effective_from<=:as_of
              AND (m.effective_to IS NULL OR m.effective_to>:as_of)
            ORDER BY ccu.ccu_code, m.national_tariff_code
        """), {"as_of": as_of})
        rows.extend(dict(item._mapping) for item in mfn_result)

        for agreement in ("ACFTA", "ATIGA", "RCEP"):
            group = origin_group(agreement, origin)
            if not group:
                continue
            result = self.session.execute(text("""
                SELECT ccu.ccu_code, ccu.ccu_name_cn, ccu.required_input_fields,
                       ccu.technical_qualifiers,
                       m.national_tariff_code, m.tariff_description, m.duty_rate,
                       m.origin_regime::text AS origin_regime,
                       a.agreement_code, m.eligibility_condition,
                       m.effective_from, m.effective_to,
                       m.verification_status::text AS verification_status,
                       d.source_code, d.document_title,
                       d.canonical_url AS official_url,
                       c.locator_value AS source_locator,
                       c.clause_code, c.evidence_summary
                FROM customs.tariff_mapping m
                JOIN ref.country n ON n.country_id=m.country_id
                JOIN ref.trade_agreement a ON a.trade_agreement_id=m.trade_agreement_id
                JOIN customs.ccu_candidate_hs h ON h.candidate_id=m.candidate_id
                JOIN customs.customs_classification_unit ccu ON ccu.ccu_id=h.ccu_id
                LEFT JOIN evidence.source_clause c ON c.source_clause_id=m.source_clause_id
                LEFT JOIN evidence.source_document d ON d.source_document_id=c.source_document_id
                WHERE n.iso2='VN' AND m.origin_regime::text='FTA'
                  AND a.agreement_code=:agreement AND m.record_status='ACTIVE'
                  AND m.effective_from<=:as_of AND (m.effective_to IS NULL OR m.effective_to>:as_of)
                  AND m.eligibility_condition->>'origin_group'=:group
                ORDER BY ccu.ccu_code, m.national_tariff_code
            """), {"agreement": agreement, "group": group, "as_of": as_of})
            rows.extend(dict(item._mapping) for item in result)

        grouped: dict[str, dict[str, Any]] = {
            ccu: {"ccu_code": ccu, "ccu_name_cn": ccu, "required_facts": [], "candidates": []}
            for ccu in weights
        }
        seen: set[tuple[str, str, str | None]] = set()
        for item in rows:
            ccu = item["ccu_code"]
            if ccu not in grouped or not self._is_candidate_eligible_for_origin(item, origin) or not self._is_passenger_component_candidate(item):
                continue
            key = (ccu, item["agreement_code"], item["national_tariff_code"])
            if key in seen:
                continue
            seen.add(key)
            group = grouped[ccu]
            group["ccu_name_cn"] = item["ccu_name_cn"]
            group["required_facts"] = item["required_input_fields"] or []
            group["candidates"].append({
                "agreement": item.get("agreement_code") or "MFN",
                "regime": "MFN" if str(item.get("origin_regime") or "").upper() == "MFN" else item.get("agreement_code"),
                "national_tariff_code": item["national_tariff_code"],
                "tariff_description": item["tariff_description"],
                "import_duty_rate": item["duty_rate"],
                "verification_status": item.get("verification_status") or "CANDIDATE",
                "status": (
                    "VERIFIED"
                    if item.get("verification_status") in {"VERIFIED", "RULING_CONFIRMED"}
                    and not item.get("eligibility_condition")
                    else "CONDITIONAL"
                ),
                "effective_from": item.get("effective_from"),
                "effective_to": item.get("effective_to"),
                "source_code": item.get("source_code"),
                "official_url": item.get("official_url"),
                "source_locator": item.get("source_locator"),
                "document_title": item.get("document_title"),
                "evidence_summary": item.get("evidence_summary"),
                "eligibility_condition": item.get("eligibility_condition") or {},
            })
        return list(grouped.values())

    @staticmethod
    def _is_candidate_eligible_for_origin(row: dict[str, Any], origin: str) -> bool:
        condition = row.get("eligibility_condition") or {}
        excluded = condition.get("excluded_origin_countries", [])
        if isinstance(excluded, str):
            excluded = [part.strip().upper() for part in excluded.replace("|", ",").split(",") if part.strip()]
        return origin.upper() not in {str(item).upper() for item in excluded}

    @staticmethod
    def _is_passenger_component_candidate(row: dict[str, Any]) -> bool:
        """Keep only passenger-car component lines for the CKD estimator.

        A shared tariff line may mention 87.02/87.03/87.04 together.  It is
        still valid for a passenger-car estimate when 87.03 is explicitly
        present.  A line that only names a non-passenger heading is excluded.
        Broad ``other`` lines remain candidates and are never auto-selected.
        """
        desc = (row.get("tariff_description") or "").upper()
        non_passenger = (
            "87.01", "87.02", "87.04", "87.05", "87.11", "TRACTOR",
            "MÁY KÉO", "MOTORCYCLE", "MOTOR CYCLE", "MÔ TÔ", "XE MÁY",
            "AIRCRAFT", "HELICOPTER", "MÁY BAY",
            "LAPTOP", "NOTEBOOK", "MÁY TÍNH XÁCH TAY",
        )
        if "87.03" in desc:
            return True
        return not any(token in desc for token in non_passenger)

    @staticmethod
    def weights(powertrain: str) -> dict[str, Decimal]:
        items = dict(DEFAULT_WEIGHTS)
        if powertrain in {"BEV", "FCEV"}:
            items.pop("VN-CKD-GASOLINE-ENGINE", None); items.pop("VN-CKD-DIESEL-ENGINE", None)
        elif powertrain == "ICE_GASOLINE":
            for k in ("VN-CKD-TRACTION-BATTERY", "VN-CKD-TRACTION-MOTOR", "VN-CKD-E-POWER-CONTROL", "VN-CKD-DIESEL-ENGINE"): items.pop(k, None)
        elif powertrain == "ICE_DIESEL":
            for k in ("VN-CKD-TRACTION-BATTERY", "VN-CKD-TRACTION-MOTOR", "VN-CKD-E-POWER-CONTROL", "VN-CKD-GASOLINE-ENGINE"): items.pop(k, None)
        else:
            items.pop("VN-CKD-DIESEL-ENGINE", None)
        total = sum(items.values())
        return {k: v / total for k, v in items.items()}

    def policy_matches(self, origin: str, as_of: date, powertrain: str, paths: tuple[str, ...]) -> list[dict[str, Any]]:
        rows = self.session.execute(text("""
            SELECT p.program_code, p.program_name_cn, p.import_mode::text import_mode, p.powertrain::text powertrain,
                   p.incentive_scope, p.condition_expression, p.benefit_expression,
                   p.effective_from, p.effective_to, p.approval_required, p.verification_status::text verification_status,
                   doc.source_code AS source_id, doc.document_title, doc.document_number,
                   doc.source_type, doc.canonical_url AS official_url,
                   auth.authority_name, clause.locator_type, clause.locator_value,
                   clause.original_text, clause.translated_text_cn, clause.evidence_summary
            FROM rules.automotive_incentive_program p JOIN ref.country c ON c.country_id=p.country_id
            LEFT JOIN evidence.source_clause clause ON clause.source_clause_id=p.source_clause_id
            LEFT JOIN evidence.source_document doc ON doc.source_document_id=clause.source_document_id
            LEFT JOIN ref.authority auth ON auth.authority_id=doc.authority_id
            WHERE c.iso2='VN' AND p.record_status='ACTIVE' AND p.effective_from<=:as_of
              AND (p.effective_to IS NULL OR p.effective_to>:as_of)
            ORDER BY program_code
        """), {"as_of": as_of})
        matched = []
        for r in [dict(x._mapping) for x in rows]:
            code = r["program_code"]; applies = []; status = "NOT_APPLICABLE"; effect = "不影响本次计算"; included = False
            if "ACFTA" in code or "ATIGA" in code or "RCEP" in code:
                a = "ACFTA" if "ACFTA" in code else ("ATIGA" if "ATIGA" in code else "RCEP")
                ok = agreement_applies(a, origin); applies = list(paths); status = "AVAILABLE_IF_ORIGIN_PROOF_CONFIRMED" if ok else "NOT_APPLICABLE_ORIGIN"; effect = f"{a}可降低进口关税" if ok else f"原产国不在{a}范围"; included = ok
            elif "BEV_SCT" in code:
                applies = list(paths); status = "APPLIED_IN_STATUTORY_OR_LOCAL_STAGE" if powertrain == "BEV" else "NOT_APPLICABLE_POWERTRAIN"; effect = "BEV低SCT；CBU已进入税链，CKD在本地成车阶段后续接入"
            elif "FIRST_REG_FEE" in code:
                applies = list(paths); status = "INFORMATION_ONLY" if powertrain == "BEV" else "NOT_APPLICABLE_POWERTRAIN"; effect = "登记费优惠不计入边境综合税率，仅作生命周期提示"
            elif "9849" in code:
                applies = ["CKD"]; status = "ENTERPRISE_CONFIRMATION_REQUIRED" if "CKD" in paths else "NOT_APPLICABLE_ROUTE"; effect = "制造/组装企业满足条件时，部分零件进口关税可0%或退税"
            elif "NEV_OUTPUT" in code:
                applies = ["CKD"]; status = "ELIGIBILITY_MODIFIER" if "CKD" in paths and powertrain in {"BEV", "FCEV", "HEV"} else "NOT_APPLICABLE"; effect = "新能源产量可影响98.49资格门槛，不直接改税率"
            matched.append({
                "program_code": code,
                "program_name_cn": r["program_name_cn"],
                "match_status": status,
                "applies_to_paths": applies,
                "incentive_scope": r["incentive_scope"],
                "approval_required": bool(r["approval_required"]),
                "effect_on_calculation": effect,
                "description": r.get("incentive_scope") or effect,
                "reason": "需企业证明时不自动落地",
                "included_in_current_numeric_result": included,
                "verification_status": r["verification_status"],
                "condition_expression": r.get("condition_expression"),
                "benefit_expression": r.get("benefit_expression"),
                "effective_from": str(r["effective_from"]) if r.get("effective_from") else None,
                "effective_to": str(r["effective_to"]) if r.get("effective_to") else None,
                "source_reference": {
                    "source_id": r.get("source_id") or "",
                    "document_title": r.get("document_title") or "",
                    "document_number": r.get("document_number"),
                    "source_type": r.get("source_type") or "",
                    "authority_name": r.get("authority_name") or "",
                    "official_url": r.get("official_url"),
                    "locator": {"locator_type": r.get("locator_type") or "", "locator_value": r.get("locator_value") or ""},
                    "original_excerpt": r.get("original_text"),
                    "translated_excerpt_cn": r.get("translated_text_cn"),
                    "evidence_summary": r.get("evidence_summary"),
                },
            })
        return matched

    @staticmethod
    def vehicle_chain(row: dict[str, Any] | None, base: Decimal, name: str) -> dict[str, Any]:
        if row is None: return VietnamQuickEstimateService.empty(name)
        dr, sr, vr = dec(row["import_duty_rate"]), dec(row["excise_duty_rate"]), dec(row["sales_tax_rate"])
        unknown = [n for n, v in (("进口关税", dr), ("特别消费税SCT", sr), ("进口VAT", vr)) if v is None]
        duty = money(base * dr) if dr is not None else Decimal("0")
        sct_base = money(base + duty); sct = money(sct_base * sr) if sr is not None else Decimal("0")
        vat_base = money(base + duty + sct); vat = money(vat_base * vr) if vr is not None else Decimal("0")
        total = money(duty + sct + vat)
        return {"name": name, "regime": row["regime"], "base_value": base, "import_duty_rate": dr, "excise_duty_rate": sr, "sales_tax_rate": vr, "known_tax_amount": total, "effective_tax_rate": rate(total / base) if not unknown else None, "tax_lines": [{"tax": "IMPORT_DUTY", "base": base, "rate": dr, "amount": duty, "formula": "海关价值 × 进口关税率"}, {"tax": "SCT", "base": sct_base, "rate": sr, "amount": sct, "formula": "（海关价值＋进口关税）× 特别消费税率"}, {"tax": "IMPORT_VAT", "base": vat_base, "rate": vr, "amount": vat, "formula": "（海关价值＋进口关税＋SCT）× VAT税率"}], "unknown_tax_items": unknown, "is_complete_statutory_chain": not unknown}

    @staticmethod
    def empty(name: str) -> dict[str, Any]:
        return {"name": name, "regime": None, "base_value": None, "known_tax_amount": None, "effective_tax_rate": None, "tax_lines": [], "unknown_tax_items": ["缺少适用税率数据"], "is_complete_statutory_chain": False}
