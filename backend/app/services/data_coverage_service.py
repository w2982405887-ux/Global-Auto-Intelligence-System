"""Data coverage service — answers "why can't this combination compute?"
and "what's available?"

Does NOT write SQL directly — goes through IntelligenceRepository and raw session queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class CoverageReport:
    coverage_status: str  # "FULL" | "PARTIAL" | "MISSING" | "UNSUPPORTED"
    available_dimensions: list[dict] = field(default_factory=list)
    missing_dimensions: list[dict] = field(default_factory=list)
    known_issues: list[str] = field(default_factory=list)
    note: str = ""


class DataCoverageService:
    """Inspect database coverage for a given powertrain/import_mode/route_code combination.

    Answers questions like "why can't HEV CBU compute?" by checking:
    - Whether rows exist for that powertrain in CBU/CKD tables
    - Whether excise_duty_rate is populated
    - Whether CKD Sedan codes exist
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # Route codes are deliberately declared by destination country.  A route
    # code is not a global fallback: accepting a MY route for a VN request was
    # the reason the agent reported Malaysia coverage for Vietnam questions.
    ROUTES_BY_COUNTRY: dict[str, dict[str, str]] = {
        "MY": {
            "CBU": "ROUTE-MY-01-CBU",
            "CKD": "ROUTE-MY-02-CKD-WHOLE-KIT",
        },
        "VN": {
            "CBU": "ROUTE-VN-01-CBU-NEW-PASSENGER",
            # Vietnam CKD is currently a logical major-parts estimate.  It is
            # backed by customs.tariff_mapping and CCU data, not by a vehicle
            # tax route row.
            "CKD": "ROUTE-VN-CKD-PARTS-MAJOR-ESTIMATE",
        },
    }

    def inspect(
        self,
        *,
        country_iso2: str = "MY",
        powertrain: str | None = None,
        import_mode: str | None = None,   # "CBU" | "CKD"
        route_code: str | None = None,
        effective_date: str | date | None = None,
    ) -> CoverageReport:
        country = (country_iso2 or "").strip().upper()
        report = CoverageReport(coverage_status="PARTIAL")

        # Date is part of the coverage key. A caller can inspect a future
        # policy window (for example 2027) without accidentally querying the
        # rules that happen to be active on the server today.
        as_of = self._parse_effective_date(effective_date)
        effective_date_label = (
            as_of.isoformat()
            if as_of is not None
            else str(effective_date or "")
        )

        if country not in self.ROUTES_BY_COUNTRY:
            report.coverage_status = "UNSUPPORTED"
            report.missing_dimensions.append(
                {
                    "country_iso2": country,
                    "route_code": route_code,
                    "effective_date": effective_date_label,
                    "import_mode": import_mode,
                    "status": "UNSUPPORTED",
                    "reason": "UNSUPPORTED_COUNTRY",
                    "total_rows": 0,
                }
            )
            report.known_issues.append(
                f"{country or '未提供'}: 尚未配置数据覆盖检查路由；未查询其他国家或回退到默认国家。"
            )
            report.note = "该目标国家尚未接入数据覆盖检查。请先配置国家路由和对应税率数据。"
            return report

        if as_of is None:
            report.coverage_status = "MISSING"
            report.missing_dimensions.append(
                {
                    "country_iso2": country,
                    "route_code": route_code,
                    "effective_date": effective_date_label,
                    "import_mode": import_mode,
                    "status": "MISSING",
                    "reason": "INVALID_EFFECTIVE_DATE",
                    "total_rows": 0,
                }
            )
            report.known_issues.append(
                "生效日期必须是 ISO 日期（YYYY-MM-DD），未执行数据库查询。"
            )
            report.note = "无法按无效生效日期判断政策覆盖。"
            return report

        powertrains = [powertrain] if powertrain else [
            "ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV", "OTHER",
        ]
        route_map = self.ROUTES_BY_COUNTRY[country]
        if route_code:
            requested_mode = (import_mode or "").strip().upper() or None
            valid_modes = [requested_mode] if requested_mode else list(route_map)
            routes = [route_code] if any(route_map.get(mode) == route_code for mode in valid_modes) else []
            if not routes:
                report.coverage_status = "UNSUPPORTED"
                report.missing_dimensions.append(
                    {
                        "country_iso2": country,
                        "route_code": route_code,
                        "effective_date": effective_date_label,
                        "import_mode": requested_mode,
                        "status": "UNSUPPORTED",
                        "reason": "ROUTE_NOT_CONFIGURED_FOR_COUNTRY",
                        "total_rows": 0,
                    }
                )
                report.known_issues.append(
                    f"{country}: 路由 {route_code} 不属于该国家已配置的覆盖检查路由。"
                )
                report.note = "未查询其他国家或默认路由。"
                return report
        else:
            requested_mode = (import_mode or "").strip().upper() or None
            if requested_mode and requested_mode not in route_map:
                report.coverage_status = "UNSUPPORTED"
                report.missing_dimensions.append(
                    {
                        "country_iso2": country,
                        "route_code": None,
                        "effective_date": effective_date_label,
                        "import_mode": requested_mode,
                        "status": "UNSUPPORTED",
                        "reason": "IMPORT_MODE_NOT_CONFIGURED_FOR_COUNTRY",
                        "total_rows": 0,
                    }
                )
                report.known_issues.append(f"{country}: 未配置 {requested_mode} 覆盖检查路由。")
                report.note = "未查询其他国家或默认路由。"
                return report
            routes = [route_map[requested_mode]] if requested_mode else list(route_map.values())

        for pt in powertrains:
            for rc in routes:
                if country == "VN" and rc == route_map["CKD"]:
                    rows = self._session.execute(
                        text("""
                            SELECT
                              count(*) AS total,
                              count(*) FILTER (WHERE mapping.duty_rate IS NOT NULL) AS has_duty,
                              count(DISTINCT ccu.ccu_code) AS component_count,
                              count(DISTINCT ccu.ccu_code) FILTER (WHERE mapping.duty_rate IS NOT NULL) AS has_duty_components,
                              count(*) FILTER (WHERE mapping.origin_regime::text = 'MFN') AS has_mfn,
                              count(*) FILTER (WHERE mapping.origin_regime::text = 'FTA') AS has_fta
                            FROM customs.tariff_mapping mapping
                            JOIN ref.country country_ref
                              ON country_ref.country_id = mapping.country_id
                            JOIN customs.ccu_candidate_hs candidate
                              ON candidate.candidate_id = mapping.candidate_id
                            JOIN customs.customs_classification_unit ccu
                              ON ccu.ccu_id = candidate.ccu_id
                            WHERE country_ref.iso2 = :country_iso2
                              AND mapping.record_status = 'ACTIVE'
                              AND mapping.effective_from <= :effective_date
                              AND (mapping.effective_to IS NULL OR mapping.effective_to > :effective_date)
                              AND ccu.technical_qualifiers->'powertrains' ? :powertrain
                        """),
                        {
                            "country_iso2": country,
                            "powertrain": pt,
                            "effective_date": as_of,
                        },
                    ).mappings().one()
                    dim = {
                        "country_iso2": country,
                        "route_code": rc,
                        "effective_date": effective_date_label,
                        "powertrain": pt,
                        "import_mode": "CKD",
                        "total_rows": int(rows["total"]),
                        "has_duty_rows": int(rows["has_duty"]),
                        "component_count": int(rows["component_count"]),
                        "has_duty_components": int(rows["has_duty_components"]),
                        "has_mfn_rows": int(rows["has_mfn"]),
                        "has_fta_rows": int(rows["has_fta"]),
                    }
                    if dim["total_rows"] == 0:
                        dim["status"] = "MISSING"
                        report.missing_dimensions.append(dim)
                        report.known_issues.append(
                            f"{country} {pt} CKD: 未找到当前有效的主要零件税率映射。"
                        )
                    elif dim["has_duty_components"] < dim["component_count"] or not dim["has_mfn_rows"]:
                        dim["status"] = "PARTIAL"
                        report.available_dimensions.append(dim)
                        if not dim["has_mfn_rows"]:
                            report.known_issues.append(
                                f"{country} {pt} CKD: 已有FTA主要零件候选，但MFN普通税率尚未完整入库。"
                            )
                        if dim["has_duty_components"] < dim["component_count"]:
                            report.known_issues.append(
                                f"{country} {pt} CKD: 部分主要零件没有有效关税率。"
                            )
                    else:
                        dim["status"] = "FULL"
                        report.available_dimensions.append(dim)
                    continue

                rows = self._session.execute(
                    text("""
                        SELECT
                          count(*) AS total,
                          count(*) FILTER (WHERE line.excise_duty_rate IS NOT NULL) AS has_excise,
                          count(*) FILTER (WHERE line.tariff_description ILIKE '%Sedan%'
                            AND line.tariff_description NOT ILIKE '%but not%'
                            AND line.tariff_description NOT ILIKE '%exceeding%') AS has_sedan
                        FROM customs.vehicle_tariff_rate_line line
                        JOIN ref.country country_ref
                          ON country_ref.country_id = line.country_id
                        JOIN rules.vehicle_tax_route route
                          ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
                        WHERE country_ref.iso2 = :country_iso2
                          AND route.route_code = :route_code
                          AND route.effective_from <= :effective_date
                          AND (route.effective_to IS NULL OR route.effective_to > :effective_date)
                          AND line.record_status = 'ACTIVE'
                          AND line.effective_from <= :effective_date
                          AND (line.effective_to IS NULL OR line.effective_to > :effective_date)
                          AND line.powertrain::text = :powertrain
                    """),
                    {
                        "country_iso2": country,
                        "route_code": rc,
                        "powertrain": pt,
                        "effective_date": as_of,
                    },
                ).mappings().one()

                dim = {
                    "country_iso2": country,
                    "route_code": rc,
                    "effective_date": effective_date_label,
                    "powertrain": pt,
                    "import_mode": "CBU" if "CBU" in rc else "CKD",
                    "total_rows": int(rows["total"]),
                    "has_excise_rows": int(rows["has_excise"]),
                    "has_sedan_codes": int(rows["has_sedan"]),
                }

                if dim["total_rows"] == 0:
                    dim["status"] = "MISSING"
                    report.missing_dimensions.append(dim)
                    report.known_issues.append(
                        f"{country} {pt} {dim['import_mode']}: 无税率数据行"
                    )
                elif dim["has_excise_rows"] == 0 and dim["import_mode"] == "CBU":
                    dim["status"] = "PARTIAL"
                    report.available_dimensions.append(dim)
                    report.known_issues.append(
                        f"{country} {pt} CBU: 有 {dim['total_rows']} 行但无一包含消费税数据 — "
                        "resolver 会 fallback 到带消费税的非 Sedan 行"
                    )
                elif dim["import_mode"] == "CKD" and dim["has_sedan_codes"] == 0:
                    dim["status"] = "PARTIAL"
                    report.available_dimensions.append(dim)
                    report.known_issues.append(
                        f"{country} {pt} CKD: 有 {dim['total_rows']} 行但无 Sedan 专用代码 — "
                        "resolver 会 fallback 到 displacement-range 代码"
                    )
                else:
                    dim["status"] = "FULL"
                    report.available_dimensions.append(dim)

        # Overall status
        all_statuses = {d["status"] for d in report.available_dimensions + report.missing_dimensions}
        if not report.available_dimensions:
            report.coverage_status = "MISSING"
        elif "MISSING" in all_statuses or "PARTIAL" in all_statuses:
            report.coverage_status = "PARTIAL"
        else:
            report.coverage_status = "FULL"

        if country == "MY":
            report.note = (
                "PHEV/EREV/FCEV CBU use OTHER powertrain mapping internally. "
                "CKD codes for HEV/PHEV/ICE mid-displacement lack Sedan-specific codes "
                "but are available via displacement-range fallback. "
                "CKD excise is NOT_AT_IMPORT for all rows."
            )
        else:
            report.note = (
                "越南CBU按越南新乘用车整车税率路线检查；越南CKD按主要零件CCU与tariff_mapping检查。"
                "越南CKD当前只覆盖主要零件进口阶段，未将本地组装后的SCT/VAT视为零。"
            )

        return report

    @staticmethod
    def _parse_effective_date(value: str | date | None) -> date | None:
        """Normalize an optional ISO date without touching the database."""
        if value is None:
            return date.today()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value).strip())
        except (TypeError, ValueError):
            return None
