from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "storage" / "evidence" / "my" / "2026-07-29"
EXTRACT = ROOT / "outputs" / "malaysia_pdk2025_research_extract.csv"

POWERTRAIN_BY_HS6 = {
    "870321": "ICE_GASOLINE",
    "870322": "ICE_GASOLINE",
    "870323": "ICE_GASOLINE",
    "870324": "ICE_GASOLINE",
    "870331": "ICE_DIESEL",
    "870332": "ICE_DIESEL",
    "870333": "ICE_DIESEL",
    "870340": "HEV",
    "870350": "HEV",
    "870360": "PHEV",
    "870370": "PHEV",
    "870380": "BEV",
}


def database_url() -> str:
    values = dotenv_values(ROOT / ".env")
    password = values.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is missing")
    return (
        f"postgresql+psycopg://{quote_plus(str(values.get('POSTGRES_USER', 'gais')))}:"
        f"{quote_plus(str(password))}@127.0.0.1:"
        f"{values.get('POSTGRES_PORT', '5432')}/{values.get('POSTGRES_DB', 'global_auto')}"
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rate(value: str) -> float:
    return float(value.strip().removesuffix("%")) / 100


def upsert_source(
    session: Session,
    *,
    source_code: str,
    authority_code: str,
    title: str,
    document_number: str | None,
    source_type: str,
    canonical_url: str,
    publication_date: date | None,
    effective_from: date | None,
    effective_to: date | None,
    file_path: Path,
) -> str:
    return str(
        session.execute(
            text(
                """
                INSERT INTO evidence.source_document (
                  source_code, authority_id, document_title, document_number,
                  source_type, official_status, canonical_url, publication_date,
                  effective_from, effective_to, accessed_at, language_code,
                  content_sha256, archived_object_key, version, record_status
                )
                SELECT
                  :source_code, authority.authority_id, :title, :document_number,
                  CAST(:source_type AS ref.source_type), 'OFFICIAL', :canonical_url,
                  :publication_date, :effective_from, :effective_to, now(), 'en-ms',
                  :content_sha256, :archived_object_key, 1, 'ACTIVE'
                FROM ref.authority authority
                WHERE authority.authority_code = :authority_code
                ON CONFLICT (source_code) DO UPDATE SET
                  document_title = EXCLUDED.document_title,
                  document_number = EXCLUDED.document_number,
                  canonical_url = EXCLUDED.canonical_url,
                  effective_from = EXCLUDED.effective_from,
                  effective_to = EXCLUDED.effective_to,
                  content_sha256 = EXCLUDED.content_sha256,
                  archived_object_key = EXCLUDED.archived_object_key,
                  record_status = 'ACTIVE'
                RETURNING source_document_id
                """
            ),
            {
                "source_code": source_code,
                "authority_code": authority_code,
                "title": title,
                "document_number": document_number,
                "source_type": source_type,
                "canonical_url": canonical_url,
                "publication_date": publication_date,
                "effective_from": effective_from,
                "effective_to": effective_to,
                "content_sha256": sha256(file_path),
                "archived_object_key": str(file_path.relative_to(ROOT)).replace("\\", "/"),
            },
        ).scalar_one()
    )


def upsert_clause(
    session: Session,
    *,
    clause_code: str,
    source_document_id: str,
    locator_value: str,
    summary: str,
) -> str:
    return str(
        session.execute(
            text(
                """
                INSERT INTO evidence.source_clause (
                  clause_code, source_document_id, locator_type, locator_value,
                  evidence_summary, extraction_method, extracted_at,
                  verification_status
                ) VALUES (
                  :clause_code, CAST(:source_document_id AS uuid), 'TARIFF_OR_POLICY_KEY',
                  :locator_value, :summary, 'OFFICIAL_DOCUMENT_AND_PORTAL_EXTRACTION',
                  now(), 'VERIFIED'
                )
                ON CONFLICT (clause_code) DO UPDATE SET
                  locator_value = EXCLUDED.locator_value,
                  evidence_summary = EXCLUDED.evidence_summary,
                  verification_status = 'VERIFIED'
                RETURNING source_clause_id
                """
            ),
            {
                "clause_code": clause_code,
                "source_document_id": source_document_id,
                "locator_value": locator_value,
                "summary": summary,
            },
        ).scalar_one()
    )


def ensure_authorities(session: Session) -> None:
    session.execute(
        text(
            """
            INSERT INTO ref.authority (
              authority_code, country_id, authority_name, official_url, record_status
            )
            SELECT code, country.country_id, name, url, 'ACTIVE'
            FROM ref.country country
            CROSS JOIN (
              VALUES
                ('MY-MOF','Ministry of Finance Malaysia','https://www.mof.gov.my'),
                ('MY-MIDA','Malaysian Investment Development Authority','https://www.mida.gov.my')
            ) item(code,name,url)
            WHERE country.iso2 = 'MY'
            ON CONFLICT (authority_code) DO UPDATE SET
              authority_name = EXCLUDED.authority_name,
              official_url = EXCLUDED.official_url,
              record_status = 'ACTIVE'
            """
        )
    )


def seed_vehicle_lines(session: Session, excise_clause_id: str) -> int:
    clause_by_hs6: dict[str, str] = {}
    rows_to_load: list[dict[str, str]] = []
    with EXTRACT.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            hs6 = row["hs6_query"]
            if hs6 not in POWERTRAIN_BY_HS6:
                continue
            if not (
                row["import_rate"] == "30%"
                and row["sst"] == "10%"
                and row["excise"].endswith("%")
            ):
                continue
            rows_to_load.append(row)

    for hs6 in POWERTRAIN_BY_HS6:
        file_path = EVIDENCE / f"JKDM_HS_Explorer_PDK2025_{hs6}.html"
        source_id = upsert_source(
            session,
            source_code=f"SRC-MY-JKDM-PDK2025-CBU-{hs6}",
            authority_code="MY-JKDM",
            title=f"JKDM HS Explorer PDK 2025 CBU query {hs6}",
            document_number="P.U. (A) 384/2025",
            source_type="OFFICIAL_PORTAL",
            canonical_url="https://ezhs.customs.gov.my/",
            publication_date=None,
            effective_from=date(2025, 11, 1),
            effective_to=None,
            file_path=file_path,
        )
        clause_by_hs6[hs6] = upsert_clause(
            session,
            clause_code=f"CLAUSE-MY-PDK2025-CBU-{hs6}",
            source_document_id=source_id,
            locator_value=f"PDK 2025 HS query {hs6}",
            summary=(
                f"Official JKDM portal result for heading branch {hs6}; exact national "
                "lines retain import duty, SST and displayed excise rates."
            ),
        )

    sql = text(
        """
        INSERT INTO customs.vehicle_tariff_line (
          line_code, country_id, tariff_version, hs6_code,
          national_tariff_code, tariff_description, import_mode,
          origin_regime, powertrain, vehicle_category,
          classification_inputs, import_duty_rate, excise_duty_rate,
          sales_tax_rate, tax_sequence, tariff_source_clause_id,
          excise_source_clause_id, effective_from, version, record_status,
          verification_status, classification_verification_status
        )
        SELECT
          :line_code, country.country_id, 'PDK 2025', :hs6,
          :national_code, :description, 'CBU', 'MFN',
          CAST(:powertrain AS ref.powertrain), 'PASSENGER_VEHICLE_8703',
          CAST(:classification_inputs AS jsonb), :import_rate, :excise_rate,
          :sst_rate,
          '["IMPORT_DUTY","EXCISE","SST"]'::jsonb,
          CAST(:tariff_clause_id AS uuid), CAST(:excise_clause_id AS uuid),
          DATE '2025-11-01', 1, 'ACTIVE', 'VERIFIED', 'CANDIDATE'
        FROM ref.country country
        WHERE country.iso2 = 'MY'
        ON CONFLICT (line_code, version) DO UPDATE SET
          tariff_description = EXCLUDED.tariff_description,
          import_duty_rate = EXCLUDED.import_duty_rate,
          excise_duty_rate = EXCLUDED.excise_duty_rate,
          sales_tax_rate = EXCLUDED.sales_tax_rate,
          tariff_source_clause_id = EXCLUDED.tariff_source_clause_id,
          excise_source_clause_id = EXCLUDED.excise_source_clause_id,
          record_status = 'ACTIVE',
          verification_status = 'VERIFIED',
          updated_at = now()
        """
    )
    for row in rows_to_load:
        hs6 = row["hs6_query"]
        session.execute(
            sql,
            {
                "line_code": f"VTL-MY-PDK2025-{row['national_tariff_code']}-MFN",
                "hs6": hs6,
                "national_code": row["national_tariff_code"],
                "description": row["description"],
                "powertrain": POWERTRAIN_BY_HS6[hs6],
                "classification_inputs": json.dumps(
                    {
                        "required": [
                            "vehicle.powertrain",
                            "vehicle.body_type",
                            "vehicle.drive_type",
                            "vehicle.engine_displacement_cc",
                            "vehicle.new_or_used",
                            "classification.parent_branch_confirmed",
                        ],
                        "hs6_branch": hs6,
                        "final_line_requires_customs_review": True,
                    }
                ),
                "import_rate": rate(row["import_rate"]),
                "excise_rate": rate(row["excise"]),
                "sst_rate": rate(row["sst"]),
                "tariff_clause_id": clause_by_hs6[hs6],
                "excise_clause_id": excise_clause_id,
            },
        )
    return len(rows_to_load)


def seed_programs(
    session: Session,
    *,
    budget_clause_id: str,
    ap_clause_id: str,
) -> None:
    programs = [
        {
            "code": "INC-MY-CKD-BEV-FULL-EXEMPTION-2027",
            "name": "马来西亚本地组装BEV税费全额豁免（项目批准型）",
            "mode": "LOCAL_PRODUCTION",
            "powertrain": "BEV",
            "scope": "CKD_EV_COMPONENT_IMPORT_AND_LOCALLY_ASSEMBLED_FINISHED_VEHICLE",
            "condition": {
                "all": [
                    {"field": "approval.miti_local_assembly_model", "operator": "EQ", "value": True},
                    {"field": "approval.manufacturing_licence_or_contract_assembly", "operator": "EQ", "value": True},
                    {"field": "vehicle.powertrain", "operator": "EQ", "value": "BEV"},
                    {"field": "vehicle.locally_assembled", "operator": "EQ", "value": True},
                    {"field": "approval.tax_exemption_confirmation", "operator": "EQ", "value": True},
                ]
            },
            "benefit": {
                "component_import_duty_rate_override": 0,
                "finished_vehicle_excise_rate_override": 0,
                "finished_vehicle_sales_tax_rate_override": 0,
                "benefit_applies_only_with_approval": True,
            },
            "source": budget_clause_id,
            "from": date(2023, 1, 1),
            "to": date(2028, 1, 1),
            "status": "VERIFIED",
        },
        {
            "code": "INC-MY-CKD-PHEV-PROJECT-APPROVAL",
            "name": "马来西亚本地组装PHEV项目激励（批准书决定）",
            "mode": "LOCAL_PRODUCTION",
            "powertrain": "PHEV",
            "scope": "CUSTOMISED_AUTOMOTIVE_INCENTIVE",
            "condition": {
                "all": [
                    {"field": "approval.miti_local_assembly_model", "operator": "EQ", "value": True},
                    {"field": "approval.project_incentive_letter", "operator": "PRESENT"},
                    {"field": "enterprise.localization_evidence", "operator": "PRESENT"},
                ]
            },
            "benefit": {
                "rate_source": "ENTERPRISE_PROJECT_APPROVAL",
                "default_excise_reduction": None,
                "default_sales_tax_reduction": None,
                "localization_threshold": None,
                "no_public_default_rate": True,
            },
            "source": ap_clause_id,
            "from": date(2026, 1, 1),
            "to": None,
            "status": "CANDIDATE",
        },
        {
            "code": "INC-MY-CKD-ICE-CUSTOMISED",
            "name": "马来西亚本地组装ICE定制激励（批准书决定）",
            "mode": "LOCAL_PRODUCTION",
            "powertrain": "ICE_GASOLINE",
            "scope": "CUSTOMISED_AUTOMOTIVE_INCENTIVE",
            "condition": {
                "all": [
                    {"field": "approval.miti_local_assembly_model", "operator": "EQ", "value": True},
                    {"field": "approval.project_incentive_letter", "operator": "PRESENT"},
                    {"field": "enterprise.localization_evidence", "operator": "PRESENT"},
                    {"field": "enterprise.vendor_development_plan", "operator": "PRESENT"},
                ]
            },
            "benefit": {
                "rate_source": "ENTERPRISE_PROJECT_APPROVAL",
                "default_excise_reduction": None,
                "default_sales_tax_reduction": None,
                "localization_threshold": None,
                "no_public_default_rate": True,
            },
            "source": ap_clause_id,
            "from": date(2026, 1, 1),
            "to": None,
            "status": "CANDIDATE",
        },
    ]
    sql = text(
        """
        INSERT INTO rules.automotive_incentive_program (
          program_code, country_id, program_name_cn, import_mode, powertrain,
          incentive_scope, condition_expression, benefit_expression,
          approval_required, approval_authority_id, source_clause_id,
          effective_from, effective_to, version, record_status,
          verification_status
        )
        SELECT
          :code, country.country_id, :name, CAST(:mode AS ref.import_mode),
          CAST(:powertrain AS ref.powertrain), :scope,
          CAST(:condition AS jsonb), CAST(:benefit AS jsonb), true,
          authority.authority_id, CAST(:source AS uuid), :effective_from,
          :effective_to, 1, 'ACTIVE',
          CAST(:status AS ref.verification_status)
        FROM ref.country country
        JOIN ref.authority authority ON authority.authority_code = 'MY-MITI'
        WHERE country.iso2 = 'MY'
        ON CONFLICT (program_code, version) DO UPDATE SET
          condition_expression = EXCLUDED.condition_expression,
          benefit_expression = EXCLUDED.benefit_expression,
          effective_from = EXCLUDED.effective_from,
          effective_to = EXCLUDED.effective_to,
          verification_status = EXCLUDED.verification_status,
          record_status = 'ACTIVE',
          updated_at = now()
        """
    )
    for item in programs:
        session.execute(
            sql,
            {
                **item,
                "condition": json.dumps(item["condition"]),
                "benefit": json.dumps(item["benefit"]),
                "effective_from": item["from"],
                "effective_to": item["to"],
            },
        )


def seed_rule_cards_and_approvals(
    session: Session,
    *,
    excise_clause_id: str,
    budget_clause_id: str,
    ap_clause_id: str,
) -> None:
    rules = [
        (
            "RULE-MY-CBU-VEHICLE-TAX-SEQUENCE-2025",
            "IMPORT_DUTY",
            "马来西亚CBU乘用车税费顺序",
            "CBU passenger vehicles use the selected PDK 2025 line for import duty, "
            "the Excise Duties Order 2025 line for excise, and SST on customs value "
            "plus import duty plus excise.",
            {"all": [{"field": "vehicle.import_mode", "operator": "EQ", "value": "CBU"}]},
            {
                "sequence": ["IMPORT_DUTY", "EXCISE", "SST"],
                "import_duty": {
                    "op": "MULTIPLY",
                    "args": [{"ref": "vehicle.customs_value"}, {"ref": "rate.import_duty"}],
                },
                "excise": {
                    "op": "MULTIPLY",
                    "args": [
                        {
                            "op": "ADD",
                            "args": [
                                {"ref": "vehicle.customs_value"},
                                {"ref": "tax.import_duty"},
                            ],
                        },
                        {"ref": "rate.excise"},
                    ],
                },
                "sst_base": {
                    "op": "ADD",
                    "args": [
                        {"ref": "vehicle.customs_value"},
                        {"ref": "tax.import_duty"},
                        {"ref": "tax.excise"},
                    ],
                },
            },
            excise_clause_id,
            "VERIFIED",
        ),
        (
            "RULE-MY-CBU-EXCISE-LINE-LOOKUP-2025",
            "EXCISE",
            "马来西亚CBU乘用车消费税税号查找",
            "The exact 10-digit vehicle line must be selected from the 2025 excise "
            "schedule using powertrain, displacement, body type and drive type.",
            {
                "all": [
                    {"field": "vehicle.national_tariff_code", "operator": "IS_NOT_NULL"},
                    {"field": "classification.parent_branch_confirmed", "operator": "EQ", "value": True},
                ]
            },
            {"rate_source": "customs.vehicle_tariff_line.excise_duty_rate"},
            excise_clause_id,
            "VERIFIED",
        ),
        (
            "RULE-MY-CKD-FINISHED-VEHICLE-EXCISE-GATE",
            "EXCISE",
            "马来西亚CKD成品车消费税批准门禁",
            "A CKD kit is not itself treated as a CBU excisable vehicle. The locally "
            "assembled finished vehicle requires an approved excise value and either "
            "the statutory rate or a project-approved reduction or exemption.",
            {
                "all": [
                    {"field": "vehicle.import_mode", "operator": "EQ", "value": "LOCAL_PRODUCTION"},
                    {"field": "approval.manufacturing_licence_or_contract_assembly", "operator": "EQ", "value": True},
                    {"field": "vehicle.approved_excise_value", "operator": "IS_NOT_NULL"},
                ]
            },
            {
                "rate_source": "ENTERPRISE_PROJECT_APPROVAL_OR_STATUTORY_LINE",
                "unknown_project_rate": "BLOCK",
            },
            ap_clause_id,
            "CANDIDATE",
        ),
        (
            "RULE-MY-CKD-BEV-FULL-EXEMPTION-2027",
            "INCENTIVE",
            "马来西亚本地组装BEV税费豁免至2027年底",
            "Subject to the approved local-assembly project and tax-exemption "
            "confirmation, qualifying CKD EV components receive import-duty exemption "
            "and the locally assembled EV receives excise and sales-tax exemption "
            "through 31 December 2027.",
            {
                "all": [
                    {"field": "vehicle.powertrain", "operator": "EQ", "value": "BEV"},
                    {"field": "vehicle.locally_assembled", "operator": "EQ", "value": True},
                    {"field": "approval.tax_exemption_confirmation", "operator": "EQ", "value": True},
                ]
            },
            {
                "component_import_duty_rate": 0,
                "finished_vehicle_excise_rate": 0,
                "finished_vehicle_sales_tax_rate": 0,
            },
            budget_clause_id,
            "VERIFIED",
        ),
        (
            "RULE-MY-LOCALIZATION-NO-PUBLIC-DEFAULT",
            "LOCALIZATION",
            "马来西亚汽车项目本地化率不得使用统一默认阈值",
            "Public policy describes customised incentives assessed on project merits. "
            "The system must read the approved project letter and localization evidence; "
            "it must not invent a universal local-content threshold or reduction rate.",
            {
                "all": [
                    {"field": "approval.project_incentive_letter", "operator": "IS_NOT_NULL"},
                    {"field": "enterprise.localization_evidence", "operator": "IS_NOT_NULL"},
                ]
            },
            {
                "threshold_source": "ENTERPRISE_PROJECT_APPROVAL",
                "benefit_source": "ENTERPRISE_PROJECT_APPROVAL",
                "missing_approval": "BLOCK_INCENTIVE_ONLY",
            },
            ap_clause_id,
            "CANDIDATE",
        ),
    ]
    rule_sql = text(
        """
        INSERT INTO rules.country_rule_card (
          rule_code, country_id, rule_domain, rule_name_cn, rule_content,
          condition_expression, formula_expression, tariff_version,
          authority_id, effective_from, effective_to, version,
          source_clause_id, record_status, verification_status,
          verified_at, verified_by
        )
        SELECT
          :code, country.country_id, CAST(:domain AS ref.rule_domain), :name,
          :content, CAST(:condition AS jsonb), CAST(:formula AS jsonb),
          'PDK 2025 / Excise Duties Order 2025', authority.authority_id,
          DATE '2025-11-01', :effective_to, 1, CAST(:source AS uuid),
          'ACTIVE', CAST(:status AS ref.verification_status),
          CASE WHEN :status = 'VERIFIED' THEN now() ELSE NULL END,
          CASE WHEN :status = 'VERIFIED' THEN 'CODEX_OFFICIAL_SOURCE_REVIEW' ELSE NULL END
        FROM ref.country country
        JOIN ref.authority authority ON authority.authority_code = 'MY-JKDM'
        WHERE country.iso2 = 'MY'
        ON CONFLICT (rule_code, version) DO UPDATE SET
          rule_content = EXCLUDED.rule_content,
          condition_expression = EXCLUDED.condition_expression,
          formula_expression = EXCLUDED.formula_expression,
          effective_to = EXCLUDED.effective_to,
          verification_status = EXCLUDED.verification_status,
          verified_at = EXCLUDED.verified_at,
          verified_by = EXCLUDED.verified_by,
          record_status = 'ACTIVE',
          updated_at = now()
        """
    )
    for code, domain, name, content, condition, formula, source, status in rules:
        session.execute(
            rule_sql,
            {
                "code": code,
                "domain": domain,
                "name": name,
                "content": content,
                "condition": json.dumps(condition),
                "formula": json.dumps(formula),
                "source": source,
                "status": status,
                "effective_to": (
                    date(2028, 1, 1)
                    if code == "RULE-MY-CKD-BEV-FULL-EXEMPTION-2027"
                    else None
                ),
            },
        )

    approvals = [
        (
            "REQ-MY-CBU-VEHICLE-AP-2026",
            "MANDATORY",
            "CBU_PASSENGER_VEHICLE",
            "CBU",
            None,
            {"all": [{"field": "vehicle.import_mode", "operator": "EQ", "value": "CBU"}]},
            ["MITI Approved Permit", "Vehicle type approval and model documents"],
            "CBU import cannot proceed without the applicable MITI AP.",
            ap_clause_id,
            "VERIFIED",
        ),
        (
            "REQ-MY-LOCAL-ASSEMBLY-MODEL-APPROVAL",
            "MANDATORY",
            "LOCALLY_ASSEMBLED_VEHICLE_PROJECT",
            "LOCAL_PRODUCTION",
            None,
            {
                "all": [
                    {"field": "approval.miti_local_assembly_model", "operator": "EQ", "value": True},
                    {"field": "approval.manufacturing_licence_or_contract_assembly", "operator": "EQ", "value": True},
                ]
            },
            ["MITI/BPI local assembly model approval", "Manufacturing licence or assembly contract"],
            "Local assembly and related incentive calculation are blocked.",
            ap_clause_id,
            "VERIFIED",
        ),
        (
            "REQ-MY-AUTOMOTIVE-CUSTOMISED-INCENTIVE-LETTER",
            "INCENTIVE_ONLY",
            "ICE_OR_PHEV_CUSTOMISED_INCENTIVE",
            "LOCAL_PRODUCTION",
            None,
            {"all": [{"field": "approval.project_incentive_letter", "operator": "IS_NOT_NULL"}]},
            [
                "MITI/MIDA project approval or incentive letter",
                "Approved localization and vendor-development conditions",
                "Approved excise and sales-tax benefit schedule",
            ],
            "Statutory taxes apply; no customised reduction may be assumed.",
            ap_clause_id,
            "CANDIDATE",
        ),
        (
            "REQ-MY-CKD-BEV-TAX-EXEMPTION-CONFIRMATION",
            "INCENTIVE_ONLY",
            "LOCALLY_ASSEMBLED_BEV",
            "LOCAL_PRODUCTION",
            "BEV",
            {
                "all": [
                    {"field": "approval.tax_exemption_confirmation", "operator": "EQ", "value": True},
                    {"field": "vehicle.locally_assembled", "operator": "EQ", "value": True},
                ]
            },
            ["Project approval", "Tax exemption confirmation", "Approved CKD component list"],
            "The system must calculate statutory duty, excise and SST without the exemption.",
            budget_clause_id,
            "VERIFIED",
        ),
    ]
    approval_sql = text(
        """
        INSERT INTO rules.approval_matrix (
          requirement_code, country_id, requirement_type, applicable_object,
          import_mode, powertrain, trigger_condition, required_document,
          authority_id, failure_consequence, effective_from, effective_to,
          version, source_clause_id, record_status, verification_status
        )
        SELECT
          :code, country.country_id, CAST(:type AS ref.requirement_type), :object,
          CAST(:mode AS ref.import_mode),
          CASE WHEN CAST(:powertrain AS text) IS NULL THEN NULL
               ELSE CAST(:powertrain AS ref.powertrain) END,
          CAST(:trigger AS jsonb), CAST(:documents AS jsonb), authority.authority_id,
          :failure, DATE '2026-01-01', :effective_to, 1, CAST(:source AS uuid),
          'ACTIVE', CAST(:status AS ref.verification_status)
        FROM ref.country country
        JOIN ref.authority authority ON authority.authority_code = 'MY-MITI'
        WHERE country.iso2 = 'MY'
        ON CONFLICT (requirement_code, version) DO UPDATE SET
          trigger_condition = EXCLUDED.trigger_condition,
          required_document = EXCLUDED.required_document,
          failure_consequence = EXCLUDED.failure_consequence,
          effective_to = EXCLUDED.effective_to,
          verification_status = EXCLUDED.verification_status,
          record_status = 'ACTIVE',
          updated_at = now()
        """
    )
    for code, typ, obj, mode, powertrain, trigger, documents, failure, source, status in approvals:
        session.execute(
            approval_sql,
            {
                "code": code,
                "type": typ,
                "object": obj,
                "mode": mode,
                "powertrain": powertrain,
                "trigger": json.dumps(trigger),
                "documents": json.dumps(documents),
                "failure": failure,
                "source": source,
                "status": status,
                "effective_to": (
                    date(2028, 1, 1)
                    if code == "REQ-MY-CKD-BEV-TAX-EXEMPTION-CONFIRMATION"
                    else None
                ),
            },
        )


def scenario_dsl(code: str, import_mode: str, powertrain: str, local: bool) -> dict:
    if local:
        inputs = [
            {"path": "vehicle.national_tariff_code", "type": "string", "required": True, "ownership": "MIXED"},
            {"path": "vehicle.approved_local_excise_value", "type": "currency", "required": True, "ownership": "ENTERPRISE"},
            {"path": "vehicle.determined_local_sales_value", "type": "currency", "required": True, "ownership": "ENTERPRISE"},
            {"path": "rate.excise", "type": "decimal", "required": True, "ownership": "MIXED"},
            {"path": "rate.sst", "type": "decimal", "required": True, "ownership": "MIXED"},
            {"path": "approval.project", "type": "object", "required": True, "ownership": "ENTERPRISE"},
        ]
        steps = [
            {
                "step_id": "LOCAL_EXCISE",
                "sequence_no": 1,
                "tax_code": "EXCISE",
                "base": {"ref": "vehicle.approved_local_excise_value"},
                "rate_source": {"type": "INPUT", "reference": "rate.excise"},
                "amount": {"op": "MULTIPLY", "args": [{"ref": "vehicle.approved_local_excise_value"}, {"ref": "rate.excise"}]},
                "on_missing": "BLOCK",
                "display_formula": "approved local excise value x statutory or project-approved rate",
            },
            {
                "step_id": "LOCAL_SST",
                "sequence_no": 2,
                "tax_code": "SST",
                "base": {"ref": "vehicle.determined_local_sales_value"},
                "rate_source": {"type": "INPUT", "reference": "rate.sst"},
                "amount": {"op": "MULTIPLY", "args": [{"ref": "vehicle.determined_local_sales_value"}, {"ref": "rate.sst"}]},
                "on_missing": "BLOCK",
                "display_formula": "determined local sales value x approved sales-tax rate",
            },
        ]
        output_code = "GROSS_LOCAL_FINISHED_VEHICLE_TAX"
        output_args = [{"ref": "tax.excise"}, {"ref": "tax.sst"}]
    else:
        inputs = [
            {"path": "vehicle.customs_value", "type": "currency", "required": True, "ownership": "ENTERPRISE"},
            {"path": "vehicle.national_tariff_code", "type": "string", "required": True, "ownership": "MIXED"},
            {"path": "rate.import_duty", "type": "decimal", "required": True, "ownership": "PUBLIC"},
            {"path": "rate.excise", "type": "decimal", "required": True, "ownership": "PUBLIC"},
            {"path": "rate.sst", "type": "decimal", "required": True, "ownership": "PUBLIC"},
        ]
        steps = [
            {
                "step_id": "IMPORT_DUTY",
                "sequence_no": 1,
                "tax_code": "IMPORT_DUTY",
                "base": {"ref": "vehicle.customs_value"},
                "rate_source": {"type": "INPUT", "reference": "rate.import_duty"},
                "amount": {"op": "MULTIPLY", "args": [{"ref": "vehicle.customs_value"}, {"ref": "rate.import_duty"}]},
                "on_missing": "BLOCK",
                "display_formula": "customs value x selected import-duty rate",
            },
            {
                "step_id": "EXCISE",
                "sequence_no": 2,
                "tax_code": "EXCISE",
                "depends_on": ["IMPORT_DUTY"],
                "base": {"op": "ADD", "args": [{"ref": "vehicle.customs_value"}, {"ref": "tax.import_duty"}]},
                "rate_source": {"type": "INPUT", "reference": "rate.excise"},
                "amount": {"op": "MULTIPLY", "args": [{"op": "ADD", "args": [{"ref": "vehicle.customs_value"}, {"ref": "tax.import_duty"}]}, {"ref": "rate.excise"}]},
                "on_missing": "BLOCK",
                "display_formula": "(customs value + import duty) x excise rate",
            },
            {
                "step_id": "SST",
                "sequence_no": 3,
                "tax_code": "SST",
                "depends_on": ["IMPORT_DUTY", "EXCISE"],
                "base": {"op": "ADD", "args": [{"ref": "vehicle.customs_value"}, {"ref": "tax.import_duty"}, {"ref": "tax.excise"}]},
                "rate_source": {"type": "INPUT", "reference": "rate.sst"},
                "amount": {"op": "MULTIPLY", "args": [{"op": "ADD", "args": [{"ref": "vehicle.customs_value"}, {"ref": "tax.import_duty"}, {"ref": "tax.excise"}]}, {"ref": "rate.sst"}]},
                "on_missing": "BLOCK",
                "display_formula": "(customs value + import duty + excise) x SST rate",
            },
        ]
        output_code = "GROSS_IMPORT_TAX"
        output_args = [{"ref": "tax.import_duty"}, {"ref": "tax.excise"}, {"ref": "tax.sst"}]
    return {
        "dsl_version": "0.1.0",
        "scenario_code": code,
        "inputs": inputs,
        "scenario_applies_when": {
            "all": [
                {"field": "vehicle.import_mode", "operator": "EQ", "value": import_mode},
                {"field": "vehicle.powertrain", "operator": "EQ", "value": powertrain},
            ]
        },
        "steps": steps,
        "outputs": [
            {
                "code": output_code,
                "expression": {
                    "op": "ADD",
                    "args": output_args,
                },
            }
        ],
        "completeness_policy": {
            "unknown_rate": "BLOCK",
            "missing_required_input": "BLOCK",
            "failed_eligibility": "FALLBACK" if local else "BLOCK",
        },
    }


def seed_scenarios(session: Session) -> None:
    definitions = [
        ("SCN-MY-CBU-ICE-MFN-2025", "马来西亚CBU ICE乘用车MFN场景", "CBU", "ICE_GASOLINE", False),
        ("SCN-MY-CBU-PHEV-MFN-2025", "马来西亚CBU PHEV乘用车MFN场景", "CBU", "PHEV", False),
        ("SCN-MY-CBU-BEV-MFN-2025", "马来西亚CBU BEV乘用车MFN场景", "CBU", "BEV", False),
        ("SCN-MY-LOCAL-ICE-PROJECT", "马来西亚本地组装ICE项目批准场景", "LOCAL_PRODUCTION", "ICE_GASOLINE", True),
        ("SCN-MY-LOCAL-PHEV-PROJECT", "马来西亚本地组装PHEV项目批准场景", "LOCAL_PRODUCTION", "PHEV", True),
        ("SCN-MY-LOCAL-BEV-EXEMPT-2027", "马来西亚本地组装BEV豁免场景", "LOCAL_PRODUCTION", "BEV", True),
    ]
    sql = text(
        """
        INSERT INTO rules.tax_scenario_model (
          scenario_code, country_id, scenario_name_cn, import_mode,
          origin_regime, powertrain, classification_route,
          required_input_fields, calculation_dsl, output_scope,
          effective_from, effective_to, version, record_status,
          verification_status
        )
        SELECT
          :code, country.country_id, :name, CAST(:mode AS ref.import_mode),
          'MFN', CAST(:powertrain AS ref.powertrain), :route,
          CAST(:inputs AS jsonb), CAST(:dsl AS jsonb),
          CAST(:output_scope AS jsonb),
          DATE '2025-11-01', :effective_to, 1, 'ACTIVE',
          CAST(:status AS ref.verification_status)
        FROM ref.country country
        WHERE country.iso2 = 'MY'
        ON CONFLICT (scenario_code, version) DO UPDATE SET
          required_input_fields = EXCLUDED.required_input_fields,
          calculation_dsl = EXCLUDED.calculation_dsl,
          output_scope = EXCLUDED.output_scope,
          effective_to = EXCLUDED.effective_to,
          verification_status = EXCLUDED.verification_status,
          record_status = 'ACTIVE',
          updated_at = now()
        """
    )
    for code, name, mode, powertrain, local in definitions:
        dsl = scenario_dsl(code, mode, powertrain, local)
        session.execute(
            sql,
            {
                "code": code,
                "name": name,
                "mode": mode,
                "powertrain": powertrain,
                "route": (
                    "LOCAL_ASSEMBLY_PROJECT_APPROVAL"
                    if local
                    else "CBU_EXACT_10_DIGIT_VEHICLE_TARIFF_LINE"
                ),
                "inputs": json.dumps([item["path"] for item in dsl["inputs"] if item["required"]]),
                "dsl": json.dumps(dsl),
                "output_scope": json.dumps(
                    {
                        "taxes": ["IMPORT_DUTY", "EXCISE", "SST"],
                        "profit_comparison": True,
                    }
                ),
                "effective_to": (
                    date(2028, 1, 1)
                    if code == "SCN-MY-LOCAL-BEV-EXEMPT-2027"
                    else None
                ),
                "status": (
                    "VERIFIED"
                    if code.startswith("SCN-MY-CBU-")
                    or code == "SCN-MY-LOCAL-BEV-EXEMPT-2027"
                    else "CANDIDATE"
                ),
            },
        )


def main() -> None:
    engine = create_engine(database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        ensure_authorities(session)
        excise_pdf = EVIDENCE / "MY_Excise_Duties_Order_2025_PUA389.pdf"
        excise_source = upsert_source(
            session,
            source_code="SRC-MY-EXCISE-DUTIES-ORDER-2025",
            authority_code="MY-JKDM",
            title="Excise Duties Order 2025",
            document_number="P.U. (A) 389/2025",
            source_type="GAZETTE",
            canonical_url=(
                "https://www.customs.gov.my/images/06-prosedur/eksais/"
                "perintah/PUA389_2025.pdf"
            ),
            publication_date=date(2025, 10, 31),
            effective_from=date(2025, 11, 1),
            effective_to=None,
            file_path=excise_pdf,
        )
        excise_clause = upsert_clause(
            session,
            clause_code="CLAUSE-MY-EXCISE-2025-CH87-8703",
            source_document_id=excise_source,
            locator_value="First Schedule, Chapter 87, heading 87.03",
            summary=(
                "Excise duty applies to listed 8703 lines at ad valorem rates; "
                "official PDK portal line results display exact rates from 10% to 105%."
            ),
        )

        ap_pdf = EVIDENCE / "MITI_AP_MRA_EV_Guideline_2026.pdf"
        ap_source = upsert_source(
            session,
            source_code="SRC-MY-MITI-AP-MRA-EV-2026",
            authority_code="MY-MITI",
            title="Guideline for AP Market Research and Pre-Assembly for EV",
            document_number=None,
            source_type="OFFICIAL_GUIDE",
            canonical_url=(
                "https://www.miti.gov.my/miti/resources/Approve%20Permit/"
                "Guidelines/GP_AP_MRA_EV_1_JAN_2026.pdf"
            ),
            publication_date=None,
            effective_from=date(2026, 1, 1),
            effective_to=date(2031, 1, 1),
            file_path=ap_pdf,
        )
        ap_clause = upsert_clause(
            session,
            clause_code="CLAUSE-MY-MITI-AP-MRA-EV-2026-ELIGIBILITY",
            source_document_id=ap_source,
            locator_value="Sections A-C, pages 1-2",
            summary=(
                "AP MRA EV requires approved local-assembly model and manufacturing "
                "licence or assembly contract; eligible categories include BEV, FCEV, "
                "PHEV and HEV."
            ),
        )

        budget_pdf = EVIDENCE / "MOF_Budget_2023_Tax_Measures.pdf"
        budget_source = upsert_source(
            session,
            source_code="SRC-MY-MOF-BUDGET2023-EV-TAX-MEASURES",
            authority_code="MY-MOF",
            title="Budget 2023 Tax Measures - Electric Vehicle Incentives",
            document_number=None,
            source_type="BUDGET_DOCUMENT",
            canonical_url=(
                "https://belanjawan.mof.gov.my/pdf/belanjawan2023/ucapan/"
                "tax-measure.pdf"
            ),
            publication_date=date(2023, 2, 24),
            effective_from=date(2023, 1, 1),
            effective_to=date(2028, 1, 1),
            file_path=budget_pdf,
        )
        budget_clause = upsert_clause(
            session,
            clause_code="CLAUSE-MY-BUDGET2023-CKD-EV-2027",
            source_document_id=budget_source,
            locator_value="Appendix II, EV incentive extension",
            summary=(
                "Full import duty exemption for locally assembled EV components and "
                "full excise duty and sales tax exemption for locally assembled CKD EV "
                "are extended through 31 December 2027."
            ),
        )

        loaded = seed_vehicle_lines(session, excise_clause)
        seed_programs(session, budget_clause_id=budget_clause, ap_clause_id=ap_clause)
        seed_rule_cards_and_approvals(
            session,
            excise_clause_id=excise_clause,
            budget_clause_id=budget_clause,
            ap_clause_id=ap_clause,
        )
        seed_scenarios(session)
        session.commit()
        print(f"CBU vehicle tariff lines loaded: {loaded}")
        print("Automotive incentive programs loaded: 3")
        print("Country rules loaded: 5")
        print("Approval requirements loaded: 4")
        print("Vehicle tax scenarios loaded: 6")
        print(f"Completed at: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
