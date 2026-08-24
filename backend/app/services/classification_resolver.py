"""HS6 / HS10 tariff-code resolution for CBU and CKD.

DB-driven: queries vehicle_tariff_rate_line by route_code, powertrain,
displacement, body_type, drive_type. Return candidates — never fabricate codes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

# ── HS6 prefix: powertrain + displacement → first 6 digits ──────────
# Used ONLY as a LIKE filter prefix, NOT to generate 10-digit codes.

HS6_RANGES: dict[str, list[tuple[int | None, int | None, str]]] = {
    "ICE_GASOLINE": [
        (0, 1000, "870321"), (1000, 1500, "870322"),
        (1500, 3000, "870323"), (3000, None, "870324"),
    ],
    "ICE_DIESEL": [
        (0, 1500, "870331"), (1500, 2500, "870332"),
        (2500, None, "870333"),
    ],
    "HEV": [
        (0, 1000, "870340"), (1000, 1500, "870340"),
        (1500, 3000, "870340"), (3000, None, "870340"),
    ],
    "PHEV": [
        (0, 1000, "870360"), (1000, 1500, "870360"),
        (1500, 3000, "870360"), (3000, None, "870360"),
    ],
    # EREV is not a stable Malaysian tariff shortcut by itself. If the range
    # extender / ICE can mechanically propel the wheels and the vehicle is
    # externally chargeable, it follows the PHEV branch (8703.60 for spark
    # ignition). A pure series EREV may be argued separately, usually needing
    # a customs ruling. Keep this empty so unresolved EREV does not silently
    # fall into 8703.90.
    "EREV": [],
    "BEV": [(None, None, "870380")],
    "FCEV": [(None, None, "870390")],
    "OTHER": [(None, None, "8703")],
}

BodyType = Literal["SEDAN", "SUV", "MPV", "HATCHBACK", "COUPE", "WAGON", "OTHER"]
DriveType = Literal["2WD", "4WD_AWD"]

# FCEV does not have a dedicated powertrain segment in the current Malaysian
# customs DB; it falls under OTHER. EREV is intentionally not mapped here:
# callers must classify the EREV architecture first instead of assuming 870390.
POWERTRAIN_DB_MAP: dict[str, str] = {
    "FCEV": "OTHER",
}

# ── Rule / Source builders ──────────────────────────────────────────


def build_rule_reference(row: dict[str, Any] | None, rule_type: str = "TARIFF_RATE") -> dict[str, Any]:
    if row is None:
        return {"rule_id": None, "rule_type": None, "rule_description": None}
    return {
        "rule_id": str(row.get("rule_id", "")),
        "rule_type": rule_type,
        "rule_description": str(row.get("tariff_description", "")),
    }


def build_source_reference(row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {
            "source_id": "", "document_title": "", "authority_name": "",
            "document_number": None, "source_type": "", "official_url": None,
            "locator": {"locator_type": "", "locator_value": ""},
        }
    return {
        "source_id": str(row.get("source_code", "")),
        "document_title": str(row.get("document_title", "")),
        "authority_name": str(row.get("authority_name", "")),
        "document_number": row.get("document_number"),
        "source_type": str(row.get("source_type", "")),
        "official_url": row.get("canonical_url"),
        "locator": {
            "locator_type": str(row.get("locator_type", "")),
            "locator_value": str(row.get("source_locator", "")),
        },
    }


# ── Dataclasses ─────────────────────────────────────────────────────


@dataclass
class ClassificationCandidate:
    national_tariff_code: str
    hs6_code: str
    tariff_description: str
    verification_status: str
    source_code: str
    source_locator: str


@dataclass
class ClassificationResult:
    status: Literal["RESOLVED", "AMBIGUOUS", "NO_MATCH"]
    candidates: list[ClassificationCandidate] = field(default_factory=list)
    selected: ClassificationCandidate | None = None
    missing_inputs: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class HsClassification:
    national_tariff_code: str
    hs6_code: str
    tariff_description: str
    verification_status: str
    source_code: str
    source_locator: str


# ── Helpers ─────────────────────────────────────────────────────────

EXCLUDE_KEYWORDS = [
    "go-karts", "go-kart",
    "all-terrain vehicles", "atv",
    "ambulances", "ambulance",
    "hearses",
    "prison vans",
    "motor-homes", "motor-home",
]

BODY_KEYWORDS: dict[str, list[str]] = {
    "SEDAN": ["Sedan"],
    "WAGON": ["Station Wagon", "Station wagons", "Wagon"],
    "SUV": ["four-wheel drive", "Other motor cars", "Other"],
    "MPV": ["Other motor cars", "Other"],
    "HATCHBACK": ["Other motor cars", "Other"],
    "COUPE": ["Other motor cars", "Other"],
    "OTHER": ["Other motor cars", "Other"],
}


def classification_condition_warning(row: dict[str, Any] | None, body_type: str, drive_type: str) -> str | None:
    if row is None:
        return None
    description = (row.get("tariff_description", "") or "").lower()
    expected = BODY_KEYWORDS.get(body_type, BODY_KEYWORDS["OTHER"])
    body_matched = any(keyword.lower() in description for keyword in expected)
    drive_matched = (
        drive_type != "4WD_AWD"
        or any(keyword in description for keyword in ["four-wheel drive", "4wd", "awd"])
    )
    if body_matched and drive_matched:
        return None
    return (
        f"当前数据库选中的税号描述为 {row.get('tariff_description', '')!r}，"
        f"但用户选择 body_type={body_type}, drive_type={drive_type}。"
        "这表示现有 PDK 候选未能完全覆盖该继续细分条件；"
        "请补充对应 PDK 行、确认是否应改选 Other motor cars / four-wheel drive 子目，"
        "或取得 JKDM Customs Ruling 后再作为最终 HS Code。"
    )



def malaysia_870360_excise_rate(national_tariff_code: str | None) -> str | None:
    """Return Excise Duties Order 2025 statutory rate for Malaysia 8703.60.

    Rates are keyed by the final 10-digit PDK subgroup.  This is used as a
    calculation-layer guardrail because PHEV / engine-drive EREV excise is not
    determined by pure electric range; it depends on vehicle subclass,
    displacement, and sometimes drive layout.
    """
    if not national_tariff_code:
        return None
    code_value = str(national_tariff_code).replace(".", "").replace(" ", "")
    if not code_value.startswith("870360") or len(code_value) < 8:
        return None
    suffix = code_value[6:8]
    rate_map = {
        "32": "0.65", "33": "0.65",
        "61": "0.75", "62": "0.75", "63": "0.75", "64": "0.80",
        "65": "0.90", "66": "1.05", "67": "1.05", "68": "1.05",
        "71": "0.75", "72": "0.75", "73": "0.75", "74": "0.80",
        "75": "0.90", "76": "1.05", "77": "1.05",
        "81": "0.75", "82": "0.75", "83": "0.75", "84": "0.80",
        "85": "0.90", "86": "1.05", "87": "1.05",
        "91": "0.60", "92": "0.60", "93": "0.65", "94": "0.75",
        "95": "0.90", "96": "1.05", "97": "1.05", "98": "1.05",
    }
    return rate_map.get(suffix)

def malaysia_870360_excise_rate_by_conditions(
    body_type: str = "SEDAN",
    drive_type: str = "4WD_AWD",
    displacement_cc: int | None = None,
) -> str | None:
    """Return 8703.60 excise rate from final-vehicle conditions.

    Useful for CKD local-assembly stage: the CKD import kit code may be a kit
    subheading, but local excise is assessed on the finished vehicle category.
    """
    if displacement_cc is None:
        return None
    if body_type == "OTHER":
        if displacement_cc <= 1500:
            return "0.60"
        if displacement_cc <= 1800:
            return "0.65"
        if displacement_cc <= 2000:
            return "0.75"
        if displacement_cc <= 2500:
            return "0.90"
        return "1.05"
    if displacement_cc <= 1800:
        return "0.75"
    if displacement_cc <= 2000:
        return "0.80"
    if displacement_cc <= 2500:
        return "0.90"
    return "1.05"
def resolve_hs6_prefix(powertrain: str, displacement_cc: int | None) -> str | None:
    """Return HS6 prefix for LIKE filtering. Never used to generate codes."""
    ranges = HS6_RANGES.get(powertrain, [])
    for lo, hi, prefix in ranges:
        if lo is None and hi is None:
            return prefix
        if lo is not None and displacement_cc is not None and displacement_cc <= lo:
            continue
        if hi is not None and displacement_cc is not None and displacement_cc > hi:
            continue
        return prefix
    if ranges:
        return ranges[0][2]
    return None


def pick_best_national_code(
    rows: list[dict[str, Any]],
    prefer_excise: bool = True,
    body_type: str = "SEDAN",
    drive_type: str = "4WD_AWD",
    displacement_cc: int | None = None,
) -> dict[str, Any] | None:
    """Pick best passenger-vehicle code from candidates.

    The user has usually already decided the broad vehicle class.  At this
    stage Malaysia's national code must be narrowed with the remaining fields:
    body type, drive layout, new/passenger status, and whether the row carries
    domestic-tax data.  This function still never fabricates a code; it only
    ranks database candidates.
    """
    if not rows:
        return None

    passenger = [
        row for row in rows
        if not any(kw in (row.get("tariff_description", "") or "").lower()
                   for kw in EXCLUDE_KEYWORDS)
    ]
    candidates = passenger if passenger else rows

    body_keywords = BODY_KEYWORDS.get(body_type, BODY_KEYWORDS["OTHER"])
    if drive_type == "4WD_AWD":
        body_keywords = ["four-wheel drive", "4wd", "awd"] + body_keywords

    def code(row: dict[str, Any]) -> str:
        return str(row.get("national_tariff_code", ""))

    def phev_category_match(row: dict[str, Any]) -> bool:
        c = code(row)
        if not c.startswith("870360"):
            return True
        # Excise Duties Order 2025 PHEV / engine-drive EREV groups:
        # 61-68 sedan; 71-77 other motor cars four-wheel drive;
        # 81-87 other motor cars non-4WD; 91-98 legal Other; 32-33 ATV.
        suffix = c[6:8]
        if body_type == "SEDAN":
            return suffix in {"61", "62", "63", "64", "65", "66", "67", "68"}
        if body_type in {"SUV", "WAGON", "COUPE", "HATCHBACK", "MPV"}:
            if drive_type == "4WD_AWD":
                return suffix in {"71", "72", "73", "74", "75", "76", "77"}
            return suffix in {"81", "82", "83", "84", "85", "86", "87"}
        if body_type == "OTHER":
            return suffix in {"91", "92", "93", "94", "95", "96", "97", "98"}
        return True

    def phev_displacement_match(row: dict[str, Any]) -> bool:
        c = code(row)
        if not c.startswith("870360"):
            return True
        suffix = c[6:8]
        if suffix in {"61", "71", "81", "91", "32"}:
            return displacement_cc is not None and displacement_cc <= 1000
        if suffix in {"62", "72", "82", "92"}:
            return displacement_cc is not None and 1000 < displacement_cc <= 1500
        if suffix in {"63", "73", "83", "93"}:
            return displacement_cc is not None and 1500 < displacement_cc <= 1800
        if suffix in {"64", "74", "84", "94"}:
            return displacement_cc is not None and 1800 < displacement_cc <= 2000
        if suffix in {"65", "75", "85", "95"}:
            return displacement_cc is not None and 2000 < displacement_cc <= 2500
        if suffix in {"66", "76", "86", "96"}:
            return displacement_cc is not None and 2500 < displacement_cc <= 3000
        if suffix == "33":
            return displacement_cc is not None and displacement_cc > 1000
        if suffix in {"67", "68", "77", "87", "97", "98"}:
            return displacement_cc is not None and displacement_cc > 3000
        return True

    exact_phev_rows = [
        row for row in candidates
        if code(row).startswith("870360")
        and phev_category_match(row)
        and phev_displacement_match(row)
    ]
    if exact_phev_rows:
        candidates = exact_phev_rows

    def desc(row: dict[str, Any]) -> str:
        return (row.get("tariff_description", "") or "")

    def has(row: dict[str, Any], keywords: list[str]) -> bool:
        d = desc(row).lower()
        return any(kw.lower() in d for kw in keywords)

    def has_excise(row: dict[str, Any]) -> bool:
        return row.get("excise_duty_rate") is not None

    def score(row: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
        d = desc(row)
        dl = d.lower()
        is_new = "new" in d and "but not" not in dl
        body_match = has(row, body_keywords)
        drive_match = drive_type != "4WD_AWD" or has(row, ["four-wheel drive", "4wd", "awd"])
        non_range = "but not exceeding" not in dl and "exceeding" not in dl
        return (
            0 if phev_category_match(row) else 1,
            0 if phev_displacement_match(row) else 1,
            0 if is_new else 1,
            0 if drive_match else 1,
            0 if body_match else 1,
            0 if (prefer_excise and has_excise(row)) else 1,
            0 if non_range else 1,
            str(row.get("national_tariff_code", "")),
        )

    return sorted(candidates, key=score)[0]


# ── Resolver ────────────────────────────────────────────────────────


class ClassificationResolver:
    """Resolve HS codes from DB. Never fabricates codes from string patterns."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve_cbu_candidates(
        self,
        *,
        effective_date: date,
        powertrain: str,
        displacement_cc: int | None = None,
        body_type: BodyType = "SEDAN",
        drive_type: DriveType = "4WD_AWD",
        route_code: str = "ROUTE-MY-01-CBU",
    ) -> ClassificationResult:
        """Return matching CBU tariff code candidates."""
        return self._resolve(
            route_code=route_code,
            effective_date=effective_date,
            powertrain=powertrain,
            displacement_cc=displacement_cc,
            body_type=body_type,
            drive_type=drive_type,
        )

    def resolve_ckd_candidates(
        self,
        *,
        effective_date: date,
        powertrain: str,
        displacement_cc: int | None = None,
        body_type: BodyType = "SEDAN",
        drive_type: DriveType = "4WD_AWD",
        route_code: str = "ROUTE-MY-02-CKD-WHOLE-KIT",
    ) -> ClassificationResult:
        """Return matching CKD whole-kit tariff code candidates."""
        return self._resolve(
            route_code=route_code,
            effective_date=effective_date,
            powertrain=powertrain,
            displacement_cc=displacement_cc,
            body_type=body_type,
            drive_type=drive_type,
        )

    def validate_confirmed_code(
        self,
        *,
        route_code: str,
        national_tariff_code: str,
        effective_date: date,
        powertrain: str,
        origin_country_iso2: str,
        displacement_cc: int | None = None,
        body_type: BodyType = "SEDAN",
        drive_type: DriveType = "4WD_AWD",
    ) -> dict[str, Any] | None:
        """Check whether a user-confirmed code exists and is active."""
        rows = _fetch_tariff_lines(
            self._session,
            route_code=route_code,
            effective_date=effective_date,
            powertrain=powertrain,
            origin_country_iso2=origin_country_iso2,
            national_tariff_code=national_tariff_code,
        )
        mfn_rows = [r for r in rows if r["origin_regime"] == "MFN"]
        if not mfn_rows:
            return None
        return pick_best_national_code(mfn_rows, body_type=body_type, drive_type=drive_type, displacement_cc=displacement_cc)

    def _resolve(
        self,
        route_code: str,
        effective_date: date,
        powertrain: str,
        displacement_cc: int | None,
        body_type: BodyType,
        drive_type: DriveType,
    ) -> ClassificationResult:
        """Core resolution logic — DB-driven, returns structured result."""
        hs6_prefix = resolve_hs6_prefix(powertrain, displacement_cc)
        if hs6_prefix is None:
            return ClassificationResult(
                status="NO_MATCH",
                missing_inputs=["powertrain", "displacement_cc"],
                note=f"无法为 powertrain={powertrain} displacement={displacement_cc} 确定HS6前缀",
            )

        rows = _fetch_tariff_lines(
            self._session,
            route_code=route_code,
            effective_date=effective_date,
            powertrain=powertrain,
            hs6_prefix=hs6_prefix,
        )

        if not rows:
            return ClassificationResult(
                status="NO_MATCH",
                missing_inputs=[],
                note=f"数据库中未找到匹配 route={route_code} powertrain={powertrain} 的税号",
            )

        best = pick_best_national_code(rows, body_type=body_type, drive_type=drive_type, displacement_cc=displacement_cc)
        if best is None:
            return ClassificationResult(
                status="NO_MATCH",
                note="无法从候选行中选出合适的税号",
            )

        # Build candidates
        seen = set()
        candidates: list[ClassificationCandidate] = []
        for row in rows:
            code = row["national_tariff_code"]
            if code in seen:
                continue
            seen.add(code)
            candidates.append(ClassificationCandidate(
                national_tariff_code=code,
                hs6_code=row["hs6_code"],
                tariff_description=row["tariff_description"],
                verification_status=row.get("verification_status", "UNVERIFIED"),
                source_code=row.get("source_code", ""),
                source_locator=row.get("source_locator", ""),
            ))

        # If only one candidate → resolved
        unique_codes = {c.national_tariff_code for c in candidates}
        if len(unique_codes) == 1:
            return ClassificationResult(
                status="RESOLVED",
                candidates=candidates,
                selected=candidates[0],
                note="唯一匹配税号",
            )

        # Multiple candidates → ambiguous — tell the user what's missing
        missing: list[str] = []
        if body_type in ("SEDAN", "OTHER"):
            missing.append("body_type")
        if drive_type == "2WD":
            missing.append("drive_type")

        return ClassificationResult(
            status="AMBIGUOUS",
            candidates=candidates,
            selected=ClassificationCandidate(
                national_tariff_code=best["national_tariff_code"],
                hs6_code=best["hs6_code"],
                tariff_description=best["tariff_description"],
                verification_status=best.get("verification_status", "UNVERIFIED"),
                source_code=best.get("source_code", ""),
                source_locator=best.get("source_locator", ""),
            ),
            missing_inputs=missing,
            note=f"存在 {len(candidates)} 个候选税号，已按乘用车与四驱业务口径自动选择最适合的记录。",
        )


# ── Shared SQL ──────────────────────────────────────────────────────


def _fetch_tariff_lines(
    session: Session,
    *,
    route_code: str,
    effective_date: date,
    powertrain: str,
    origin_country_iso2: str = "",
    hs6_prefix: str = "",
    national_tariff_code: str = "",
) -> list[dict[str, Any]]:
    """Unified tariff-line reader. Filter by hs6_prefix OR exact code."""
    # Map user-facing powertrain to DB powertrain (EREV/FCEV → OTHER)
    db_powertrain = POWERTRAIN_DB_MAP.get(powertrain, powertrain)
    clauses = [
        "route.route_code = :route_code",
        "line.record_status = 'ACTIVE'",
        "line.effective_from <= :effective_date",
        "(line.effective_to IS NULL OR line.effective_to > :effective_date)",
        "line.powertrain::text = :powertrain",
    ]
    params: dict[str, Any] = {
        "route_code": route_code,
        "effective_date": effective_date,
        "powertrain": db_powertrain,
    }

    if national_tariff_code:
        clauses.append("line.national_tariff_code = :code")
        params["code"] = national_tariff_code
    elif hs6_prefix:
        clauses.append("line.national_tariff_code LIKE :hs6_pattern")
        params["hs6_pattern"] = f"{hs6_prefix}%"

    if origin_country_iso2:
        clauses.append(
            "(line.origin_regime::text = 'MFN'"
            " OR line.eligibility_condition->>'origin_country_iso2' = :origin)"
        )
        params["origin"] = origin_country_iso2.upper()

    sql = f"""
        SELECT
          line.vehicle_tariff_rate_line_id AS rule_id,
          line.rate_line_code,
          line.national_tariff_code,
          line.hs6_code,
          line.tariff_description,
          line.origin_regime::text AS origin_regime,
          COALESCE(agreement.agreement_code, 'MFN') AS agreement_code,
          line.import_duty_rate,
          line.excise_duty_rate,
          line.sales_tax_rate,
          line.sales_tax_treatment::text AS sales_tax_treatment,
          line.excise_treatment::text   AS excise_treatment,
          line.eligibility_condition,
          line.verification_status::text AS verification_status,
          doc.source_code,
          clause.locator_type,
          clause.locator_value AS source_locator,
          doc.document_title,
          doc.document_number,
          doc.source_type,
          doc.canonical_url,
          auth.authority_name
        FROM customs.vehicle_tariff_rate_line line
        JOIN rules.vehicle_tax_route route
          ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
        LEFT JOIN ref.trade_agreement agreement
          ON agreement.trade_agreement_id = line.trade_agreement_id
        JOIN evidence.source_clause clause
          ON clause.source_clause_id = line.tariff_source_clause_id
        JOIN evidence.source_document doc
          ON doc.source_document_id = clause.source_document_id
        LEFT JOIN ref.authority auth
          ON auth.authority_id = doc.authority_id
        WHERE {' AND '.join(clauses)}
        ORDER BY
          CASE WHEN line.origin_regime::text = 'MFN' THEN 0 ELSE 1 END,
          CASE WHEN line.tariff_description LIKE '%New%' THEN 0 ELSE 1 END,
          line.national_tariff_code
    """

    result = session.execute(text(sql), params)
    return [dict(row._mapping) for row in result]
