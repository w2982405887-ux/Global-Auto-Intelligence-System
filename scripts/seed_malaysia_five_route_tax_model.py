from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from dotenv import dotenv_values
from pypdf import PdfReader
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_2028 = ROOT / "storage" / "evidence" / "my" / "2026-07-28"
EVIDENCE_2029 = ROOT / "storage" / "evidence" / "my" / "2026-07-29"
PDK_EXTRACT = ROOT / "outputs" / "malaysia_pdk2025_research_extract.csv"
FTA_EXTRACT = ROOT / "outputs" / "malaysia_fta_2026_research_extract.csv"

VEHICLE_HS6 = (
    "870321",
    "870322",
    "870323",
    "870324",
    "870331",
    "870332",
    "870333",
    "870340",
    "870350",
    "870360",
    "870370",
    "870380",
    "870390",
)

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
    "870390": "OTHER",
}

ROUTE_CBU = "ROUTE-MY-01-CBU"
ROUTE_CKD = "ROUTE-MY-02-CKD-WHOLE-KIT"
ROUTE_SUBASSEMBLIES = "ROUTE-MY-03-PARTS-SUBASSEMBLIES"
ROUTE_PART_LEVEL = "ROUTE-MY-04-PART-LEVEL"
ROUTE_MIXED = "ROUTE-MY-05-MIXED-KD"


def database_url() -> str:
    values = dotenv_values(ROOT / ".env")
    password = values.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is missing")
    return (
        f"postgresql+psycopg://{quote_plus(str(values.get('POSTGRES_USER', 'gais')))}:"
        f"{quote_plus(str(password))}@127.0.0.1:"
        f"{values.get('POSTGRES_PORT', '5432')}/"
        f"{values.get('POSTGRES_DB', 'global_auto')}"
    )


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_rate(value: str) -> float | None:
    normalized = value.strip()
    if not normalized:
        return None
    return float(normalized.removesuffix("%")) / 100


def ensure_reference_data(session: Session) -> None:
    session.execute(
        text(
            """
            INSERT INTO ref.authority (
              authority_code, country_id, authority_name, official_url, record_status
            )
            SELECT item.code, country.country_id, item.name, item.url, 'ACTIVE'
            FROM ref.country country
            CROSS JOIN (
              VALUES
                ('MY-JKDM', 'Royal Malaysian Customs Department',
                 'https://www.customs.gov.my'),
                ('MY-MITI', 'Ministry of Investment, Trade and Industry',
                 'https://www.miti.gov.my'),
                ('MY-MOF', 'Ministry of Finance Malaysia',
                 'https://www.mof.gov.my'),
                ('MY-MIDA', 'Malaysian Investment Development Authority',
                 'https://www.mida.gov.my')
            ) item(code, name, url)
            WHERE country.iso2 = 'MY'
            ON CONFLICT (authority_code) DO UPDATE SET
              authority_name = EXCLUDED.authority_name,
              official_url = EXCLUDED.official_url,
              record_status = 'ACTIVE',
              updated_at = now()
            """
        )
    )
    session.execute(
        text(
            """
            INSERT INTO ref.trade_agreement (
              agreement_code, agreement_name, version, effective_from, record_status
            ) VALUES
              ('ACFTA', 'ASEAN-China Free Trade Area', 1, DATE '2005-07-20', 'ACTIVE'),
              ('RCEP', 'Regional Comprehensive Economic Partnership', 1,
               DATE '2022-03-18', 'ACTIVE')
            ON CONFLICT (agreement_code, version) DO UPDATE SET
              agreement_name = EXCLUDED.agreement_name,
              record_status = 'ACTIVE'
            """
        )
    )


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
    file_path: Path | None,
) -> str:
    content_hash = sha256(file_path) if file_path is not None else None
    object_key = (
        str(file_path.relative_to(ROOT)).replace("\\", "/")
        if file_path is not None
        else None
    )
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
                  source_type = EXCLUDED.source_type,
                  official_status = 'OFFICIAL',
                  canonical_url = EXCLUDED.canonical_url,
                  publication_date = EXCLUDED.publication_date,
                  effective_from = EXCLUDED.effective_from,
                  effective_to = EXCLUDED.effective_to,
                  accessed_at = now(),
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
                "content_sha256": content_hash,
                "archived_object_key": object_key,
            },
        ).scalar_one()
    )


def upsert_clause(
    session: Session,
    *,
    clause_code: str,
    source_document_id: str,
    locator_type: str,
    locator_value: str,
    summary: str,
    verification_status: str = "VERIFIED",
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
                  :clause_code, CAST(:source_document_id AS uuid), :locator_type,
                  :locator_value, :summary, 'OFFICIAL_DOCUMENT_AND_PORTAL_REVIEW',
                  now(), CAST(:verification_status AS ref.verification_status)
                )
                ON CONFLICT (clause_code)
                DO UPDATE SET
                  source_document_id = EXCLUDED.source_document_id,
                  locator_type = EXCLUDED.locator_type,
                  locator_value = EXCLUDED.locator_value,
                  evidence_summary = EXCLUDED.evidence_summary,
                  extraction_method = EXCLUDED.extraction_method,
                  extracted_at = now(),
                  verification_status = EXCLUDED.verification_status
                RETURNING source_clause_id
                """
            ),
            {
                "clause_code": clause_code,
                "source_document_id": source_document_id,
                "locator_type": locator_type,
                "locator_value": locator_value,
                "summary": summary,
                "verification_status": verification_status,
            },
        ).scalar_one()
    )


def seed_policy_sources(session: Session) -> dict[str, str]:
    source_specs = {
        "sst_exempt_2025": {
            "source_code": "SRC-MY-SST-GOODS-EXEMPT-2025",
            "authority_code": "MY-JKDM",
            "title": "Sales Tax (Goods Exempted from Sales Tax) Order 2025",
            "document_number": "P.U. (A) 171/2025",
            "source_type": "GAZETTE",
            "canonical_url": (
                "https://pub-359af8e1f79c472292a7e44ec60f3027.r2.dev/"
                "SST%20Orders/3-PUA%20171%20(2025).pdf"
            ),
            "publication_date": date(2025, 6, 9),
            "effective_from": date(2025, 7, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_Sales_Tax_Goods_Exempted_Order_2025_PUA171.pdf",
        },
        "sst_exempt_amend_2025": {
            "source_code": "SRC-MY-SST-GOODS-EXEMPT-AMEND-2025",
            "authority_code": "MY-JKDM",
            "title": (
                "Sales Tax (Goods Exempted from Sales Tax) "
                "(Amendment) Order 2025"
            ),
            "document_number": "P.U. (A) 200/2025",
            "source_type": "GAZETTE",
            "canonical_url": (
                "https://mysst.customs.gov.my/assets/document/SST%20Orders/"
                "3-PUA%20200%20(2025).pdf"
            ),
            "publication_date": date(2025, 6, 30),
            "effective_from": date(2025, 7, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_Sales_Tax_Goods_Exempted_Amendment_Order_2025_PUA200.pdf",
        },
        "sst_rate_2025": {
            "source_code": "SRC-MY-SST-RATE-ORDER-2025",
            "authority_code": "MY-JKDM",
            "title": "Sales Tax (Rate of Sales Tax) Order 2025",
            "document_number": "P.U. (A) 170/2025",
            "source_type": "GAZETTE",
            "canonical_url": (
                "https://pub-359af8e1f79c472292a7e44ec60f3027.r2.dev/"
                "SST%20Orders/1-PUA%20170_2025.pdf"
            ),
            "publication_date": date(2025, 6, 9),
            "effective_from": date(2025, 7, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_Sales_Tax_Rate_Order_2025_PUA170.pdf",
        },
        "sst_value_2018": {
            "source_code": "SRC-MY-SST-SALE-VALUE-REGULATIONS-2018",
            "authority_code": "MY-JKDM",
            "title": (
                "Sales Tax (Determination of Sale Value of Taxable Goods) "
                "Regulations 2018"
            ),
            "document_number": "P.U. (A) 205/2018",
            "source_type": "REGULATION",
            "canonical_url": (
                "https://mysst.customs.gov.my/wp-content/uploads/2025/03/"
                "Sales-Tax-Determination-Of-Sale-Value-Of-Taxable-Goods-"
                "Regulations-2018.pdf"
            ),
            "publication_date": date(2018, 8, 28),
            "effective_from": date(2018, 9, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_Sales_Tax_Sale_Value_Regulations_2018_PUA205.pdf",
        },
        "excise_2025": {
            "source_code": "SRC-MY-EXCISE-DUTIES-ORDER-2025",
            "authority_code": "MY-JKDM",
            "title": "Excise Duties Order 2025",
            "document_number": "P.U. (A) 389/2025",
            "source_type": "GAZETTE",
            "canonical_url": (
                "https://www.customs.gov.my/images/06-prosedur/eksais/"
                "perintah/PUA389_2025.pdf"
            ),
            "publication_date": date(2025, 10, 31),
            "effective_from": date(2025, 11, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_Excise_Duties_Order_2025_PUA389.pdf",
        },
        "excise_payment_2026": {
            "source_code": "SRC-MY-EXCISE-MOTOR-VEHICLE-PAYMENT-2026",
            "authority_code": "MY-JKDM",
            "title": "Excise (Payment of Excise Duties for Motor Vehicles) Order 2026",
            "document_number": "P.U. (A) 44/2026",
            "source_type": "GAZETTE",
            "canonical_url": (
                "https://www.customs.gov.my/images/06-prosedur/eksais/"
                "perintah/PUA%2044_2026.pdf"
            ),
            "publication_date": date(2026, 1, 30),
            "effective_from": date(2026, 2, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_Excise_Payment_Motor_Vehicles_Order_2026_PUA44.pdf",
        },
        "excise_local_value": {
            "source_code": "SRC-MY-EXCISE-LOCAL-VALUE-2019",
            "authority_code": "MY-JKDM",
            "title": (
                "Excise (Determination of Value of Locally Manufactured Goods "
                "for the Purpose of Levying Excise Duty) Regulations 2019"
            ),
            "document_number": "P.U. (A) 402/2019",
            "source_type": "REGULATION",
            "canonical_url": (
                "https://www.customs.gov.my/images/06-prosedur/eksais/"
                "peraturan/P.U.A402-peraturan-eksais-penentuan-nilai-barang-"
                "yang-dikilangkan-secara-tempatan.pdf"
            ),
            "publication_date": date(2019, 12, 31),
            "effective_from": date(2020, 1, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_Excise_Local_Valuation_Regulations_2019_PUA402.pdf",
        },
        "automotive_guide": {
            "source_code": "SRC-MY-JKDM-AUTOMOTIVE-GUIDE-2018",
            "authority_code": "MY-JKDM",
            "title": "Guide on Automotive Industry",
            "document_number": None,
            "source_type": "OFFICIAL_GUIDE",
            "canonical_url": (
                "https://mysst.customs.gov.my/assets/document/Industry%20Guides/"
                "GI/GuideOnAutomotiveIndustry.pdf"
            ),
            "publication_date": date(2018, 8, 23),
            "effective_from": date(2018, 9, 1),
            "effective_to": None,
            "file_path": None,
        },
        "mysst_faq": {
            "source_code": "SRC-MY-MYSST-BUSINESS-FAQ-2026",
            "authority_code": "MY-JKDM",
            "title": "MySST Business FAQ - Automotive Industry",
            "document_number": None,
            "source_type": "OFFICIAL_PORTAL",
            "canonical_url": "https://mysst.customs.gov.my/faq-business/",
            "publication_date": None,
            "effective_from": date(2026, 7, 29),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_MySST_FAQ_Business_2026-07-29.html",
        },
        "ckd_notice": {
            "source_code": "SRC-MY-MITI-CKD-AP-NOTICE-2023",
            "authority_code": "MY-MITI",
            "title": "MITI Notice on CKD Definition and AP Categories",
            "document_number": None,
            "source_type": "OFFICIAL_GUIDE",
            "canonical_url": (
                "https://www.miti.gov.my/miti/resources/Approve%20Permit/"
                "AP%20Announcement/NOTIS_MENGENAI_PERMOHONAN_LESEN_IMPORT_"
                "%28AP%29_COMPLETELY_KNOCKED_DOWN_%28CKD%29_SUSULAN_"
                "PENGUATKUASAAN_PERINTAH_KASTAM_1988_%28LATEST%29.pdf"
            ),
            "publication_date": None,
            "effective_from": date(2023, 1, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_MITI_CKD_Definition_AP_Notice.pdf",
        },
        "n205": {
            "source_code": "SRC-MY-MITI-N205-PARTS-SUBASSEMBLIES",
            "authority_code": "MY-MITI",
            "title": "MITI AP N205 Parts and Sub-Assemblies Application Flow",
            "document_number": "AP Category N205",
            "source_type": "OFFICIAL_GUIDE",
            "canonical_url": (
                "https://www.miti.gov.my/miti/resources/Approve%20Permit/"
                "Motor%20vehicle/FLOW_CHART_FOR_APPLICATION_AP_TYPE_%28INQ%29_"
                "%E2%80%93_OTHER_VEHICLE_PERMANENT_IMPORT_%E2%80%93_PARTS_"
                "SUB-ASSEMBLIES.pdf"
            ),
            "publication_date": None,
            "effective_from": date(2023, 1, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_MITI_N205_Parts_Subassemblies_AP_Flow.pdf",
        },
        "n180": {
            "source_code": "SRC-MY-MITI-N180-CBU",
            "authority_code": "MY-MITI",
            "title": "MITI AP N180 Other Vehicle CBU Application Flow",
            "document_number": "AP Category N180",
            "source_type": "OFFICIAL_GUIDE",
            "canonical_url": (
                "https://www.miti.gov.my/miti/resources/Approve%20Permit/"
                "Motor%20vehicle/11_OTHER_VEHICLE_PERMANENT_IMPORT_"
                "%E2%80%93_COMPLETELY_BUILD_UP_%28CBU%29.pdf"
            ),
            "publication_date": None,
            "effective_from": date(2026, 1, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_MITI_Other_Vehicle_CBU_AP_Flow.pdf",
        },
        "franchise_ap": {
            "source_code": "SRC-MY-MITI-FRANCHISE-AP-POLICY-2026",
            "authority_code": "MY-MITI",
            "title": "MITI Franchise AP Policy",
            "document_number": None,
            "source_type": "OFFICIAL_GUIDE",
            "canonical_url": (
                "https://www.miti.gov.my/miti/resources/Approve%20Permit/"
                "Franchise%20AP/DASAR_AP_FRANCAIS_2026_2.pdf"
            ),
            "publication_date": date(2025, 12, 1),
            "effective_from": date(2026, 1, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_MITI_Franchise_AP_Policy_2026.pdf",
        },
        "cbu_ev_2026": {
            "source_code": "SRC-MY-MITI-CBU-EV-REQUIREMENTS-2026",
            "authority_code": "MY-MITI",
            "title": "End of Special Exemption for Imported CBU Electric Vehicles",
            "document_number": None,
            "source_type": "OFFICIAL_GUIDE",
            "canonical_url": (
                "https://www.miti.gov.my/miti/resources/Media%20Release/"
                "SIARAN_MEDIA_PENAMATAN_PENGECUALIAN_KHAS_6_Mei_2026_edited.pdf"
            ),
            "publication_date": date(2026, 5, 6),
            "effective_from": date(2026, 7, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_MITI_CBU_EV_Special_Exemption_End_2026.pdf",
        },
        "budget_ev": {
            "source_code": "SRC-MY-MOF-BUDGET2023-EV-TAX-MEASURES",
            "authority_code": "MY-MOF",
            "title": "Budget 2023 Tax Measures - Electric Vehicle Incentives",
            "document_number": None,
            "source_type": "BUDGET_DOCUMENT",
            "canonical_url": (
                "https://belanjawan.mof.gov.my/pdf/belanjawan2023/ucapan/"
                "tax-measure.pdf"
            ),
            "publication_date": date(2023, 2, 24),
            "effective_from": date(2023, 1, 1),
            "effective_to": date(2028, 1, 1),
            "file_path": EVIDENCE_2029 / "MOF_Budget_2023_Tax_Measures.pdf",
        },
        "mida_ipr": {
            "source_code": "SRC-MY-MIDA-IPR-2025-EV",
            "authority_code": "MY-MIDA",
            "title": "MIDA Investment Performance Report 2025",
            "document_number": None,
            "source_type": "OFFICIAL_GUIDE",
            "canonical_url": (
                "https://www.mida.gov.my/wp-content/uploads/2026/03/"
                "MIDA_IPR.2025.pdf"
            ),
            "publication_date": date(2026, 3, 1),
            "effective_from": date(2026, 1, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_MIDA_Investment_Performance_Report_2025.pdf",
        },
        "mida_components": {
            "source_code": "SRC-MY-MIDA-COMPONENT-EXEMPTION-GUIDE",
            "authority_code": "MY-MIDA",
            "title": (
                "Guidelines for Import Duty and Sales Tax Exemption on Raw "
                "Materials and Components for Manufacturing Sectors"
            ),
            "document_number": None,
            "source_type": "OFFICIAL_GUIDE",
            "canonical_url": (
                "https://www.mida.gov.my/wp-content/uploads/2020/12/"
                "20200804164306_GD_PC_RawMaterials_29072020.pdf"
            ),
            "publication_date": date(2020, 7, 29),
            "effective_from": date(2020, 7, 29),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_MIDA_Raw_Materials_Components_Import_Duty_"
            "Exemption_Guideline.pdf",
        },
        "acfta_order": {
            "source_code": "SRC-MY-ACFTA-CUSTOMS-DUTIES-2024",
            "authority_code": "MY-JKDM",
            "title": "ACFTA Customs Duties Order 2024",
            "document_number": "P.U. (A) 454/2024",
            "source_type": "TARIFF_SCHEDULE",
            "canonical_url": (
                "https://www.customs.gov.my/images/06-prosedur/perintah-kastam/"
                "perjanjian/PUA454_2024.pdf"
            ),
            "publication_date": date(2024, 12, 27),
            "effective_from": date(2025, 1, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2028 / "JKDM_PUA454_2024_ACFTA.pdf",
        },
        "acfta_roo": {
            "source_code": "SRC-MY-MITI-ACFTA-REVISED-ROO",
            "authority_code": "MY-MITI",
            "title": "Revised ACFTA Rules of Origin",
            "document_number": None,
            "source_type": "TREATY",
            "canonical_url": (
                "https://www.miti.gov.my/miti/resources/Preferential%20"
                "Certificate%20of%20Origin/ACFTA/Revised_ACFTA_ROO.pdf"
            ),
            "publication_date": None,
            "effective_from": date(2019, 8, 1),
            "effective_to": None,
            "file_path": EVIDENCE_2028 / "MITI_ACFTA_Revised_ROO_Main.pdf",
        },
        "rcep_psr": {
            "source_code": "SRC-MY-MITI-RCEP-ANNEX-3A-PSR",
            "authority_code": "MY-MITI",
            "title": "RCEP Annex 3A Product-Specific Rules",
            "document_number": None,
            "source_type": "TREATY",
            "canonical_url": (
                "https://fta.miti.gov.my/miti-fta/resources/RCEP/"
                "Legal%20Text%20of%20the%20RCEP%20Agreement/Annex_3A.pdf"
            ),
            "publication_date": None,
            "effective_from": date(2022, 3, 18),
            "effective_to": None,
            "file_path": EVIDENCE_2028 / "MITI_RCEP_Annex_3A_PSR_HS2012.pdf",
        },
        "rcep_amend_2026": {
            "source_code": "SRC-MY-RCEP-AMENDMENT-2026",
            "authority_code": "MY-JKDM",
            "title": "RCEP Customs Duties Amendment Order 2026",
            "document_number": "P.U. (A) 127/2026",
            "source_type": "TARIFF_SCHEDULE",
            "canonical_url": (
                "https://www.customs.gov.my/images/06-prosedur/perintah-kastam/"
                "perintah/PUA_127_2026.pdf"
            ),
            "publication_date": date(2026, 3, 30),
            "effective_from": date(2026, 3, 31),
            "effective_to": None,
            "file_path": EVIDENCE_2028 / "JKDM_PUA127_2026_RCEP_Amendment.pdf",
        },
        "prohibition_2023": {
            "source_code": "SRC-MY-CUSTOMS-PROHIBITION-IMPORTS-2023",
            "authority_code": "MY-JKDM",
            "title": "Customs (Prohibition of Imports) Order 2023",
            "document_number": "P.U. (A) 117/2023",
            "source_type": "GAZETTE",
            "canonical_url": (
                "https://www.customs.gov.my/images/06-prosedur/perintah-kastam/"
                "larangan-import/PUA117-perintah_kastamlarangan_mengenai_"
                "import_2023.pdf"
            ),
            "publication_date": date(2023, 4, 13),
            "effective_from": date(2023, 4, 15),
            "effective_to": None,
            "file_path": EVIDENCE_2029
            / "MY_Customs_Prohibition_Imports_Order_2023_PUA117.pdf",
        },
    }
    source_ids = {
        key: upsert_source(session, **spec) for key, spec in source_specs.items()
    }

    clause_specs = {
        "ckd_sst_exempt": (
            "sst_exempt_2025",
            "CLAUSE-MY-PUA171-8703-CKD-SST-EXEMPT",
            "Schedule, heading 87.03, PDF pages 84-91",
            "The Schedule lists 167 exact 8703 CKD national tariff lines as goods "
            "exempted from sales tax. The 2025 amendment does not amend Chapter 87.",
        ),
        "sst_amend_no_ch87": (
            "sst_exempt_amend_2025",
            "CLAUSE-MY-PUA200-NO-CHAPTER87-CHANGE",
            "Amendment of Schedule, paragraphs 2(a)-(k)",
            "The amendment changes listed food and other headings but does not amend "
            "heading 87.03 or Chapter 87.",
        ),
        "local_sst_value": (
            "sst_value_2018",
            "CLAUSE-MY-PUA205-LOCAL-SST-VALUE",
            "Regulations 3-9; English text pages 20 onward",
            "Transaction value is primary; connected-party, no-sale and contract "
            "manufacturing cases use the prescribed alternative valuation sequence, "
            "including computed value when applicable.",
        ),
        "excise_8703": (
            "excise_2025",
            "CLAUSE-MY-EXCISE-2025-CH87-8703",
            "First Schedule, Chapter 87, heading 87.03",
            "Excise duty rates for passenger motor vehicles are determined by the "
            "exact 8703 statutory line.",
        ),
        "local_excise_payment": (
            "excise_payment_2026",
            "CLAUSE-MY-PUA44-LOCAL-MOTOR-VEHICLE-EXCISE",
            "Paragraphs 1-3 and Schedule",
            "From 1 February 2026 a licensed manufacturer pays the applicable Excise "
            "Duties Order 2025 rate when a listed locally manufactured motor vehicle "
            "is removed for registration.",
        ),
        "local_excise_value": (
            "excise_local_value",
            "CLAUSE-MY-PUA402-LOCAL-EXCISE-VALUE",
            "Regulations 3-5, English text pages 10-15",
            "Locally manufactured excisable goods use open-market value determined "
            "through computed value or flexible value; computed value includes "
            "materials, manufacturing, profit and general expenses.",
        ),
        "cbu_tax_sequence": (
            "automotive_guide",
            "CLAUSE-MY-AUTOMOTIVE-GUIDE-CBU-TAX-SEQUENCE",
            "Imported CBU worked example, PDF page 17",
            "For imported CBU vehicles the guide calculates import duty on customs "
            "value, excise on customs value plus import duty, and sales tax on customs "
            "value plus import duty plus excise.",
        ),
        "local_vehicle_sst": (
            "mysst_faq",
            "CLAUSE-MY-MYSST-FAQ-LOCAL-VEHICLE-SST",
            "Automotive Industry questions 1-5",
            "CKD components are used to assemble a finished vehicle; sales tax is "
            "charged on the finished locally assembled vehicle using transaction or "
            "computed value as applicable.",
        ),
        "ckd_route": (
            "ckd_notice",
            "CLAUSE-MY-MITI-CKD-VS-N205",
            "Full notice",
            "From 1 January 2023 a shipment meeting the Customs Regulations CKD "
            "definition uses AP CKD; one that does not meet the definition uses AP "
            "Parts/Sub-Assemblies under N205.",
        ),
        "n205_ap": (
            "n205",
            "CLAUSE-MY-MITI-N205-PARTS-SUBASSEMBLIES",
            "Flow chart and required-document lists",
            "N205 covers permanent import of vehicle parts and sub-assemblies and "
            "requires local-assembly model approval, ePermit and supporting documents.",
        ),
        "n180_ap": (
            "n180",
            "CLAUSE-MY-MITI-N180-CBU",
            "Flow chart and required-document lists",
            "N180 covers permanent import of CBU other vehicles; model and quota "
            "approval precede the online ePermit application.",
        ),
        "franchise_allocation": (
            "franchise_ap",
            "CLAUSE-MY-MITI-FRANCHISE-AP-ALLOCATION",
            "Sections B-C, pages 1-4",
            "Franchise CBU imports require an approved franchise AP holder and annual "
            "AP allocation; the allocation and permit have specified validity periods.",
        ),
        "cbu_ev_current": (
            "cbu_ev_2026",
            "CLAUSE-MY-MITI-CBU-EV-2026-07",
            "Media release page 1",
            "The special CBU EV exemption ended on 31 December 2025. From 1 July 2026 "
            "CBU EV imports are subject to minimum CIF RM200,000 and motor power of at "
            "least 180 kW.",
        ),
        "local_bev_2027": (
            "budget_ev",
            "CLAUSE-MY-BUDGET2023-CKD-EV-2027",
            "Appendix II, EV incentive extension",
            "Import-duty exemption for qualifying locally assembled EV components and "
            "excise and sales-tax exemptions for qualifying locally assembled CKD EVs "
            "are extended through 31 December 2027.",
        ),
        "customised_incentive": (
            "mida_ipr",
            "CLAUSE-MY-MIDA-IPR2025-EV-CUSTOMISED-INCENTIVE",
            "Electric Vehicles Industry, pages 56-59",
            "CBU EV exemptions ended in 2025, CKD EV incentives continue through 2027, "
            "and the new customised mechanism determines excise reduction for "
            "qualifying projects.",
        ),
        "component_exemption": (
            "mida_components",
            "CLAUSE-MY-MIDA-COMPONENT-DUTY-EXEMPTION",
            "Guidelines paragraphs 1-7",
            "Manufacturers may apply before import for duty exemption on directly "
            "imported raw materials and components used directly in finished products; "
            "the exemption is approval-gated and not automatic.",
        ),
        "acfta_roo_8703": (
            "acfta_roo",
            "CLAUSE-MY-ACFTA-8703-RVC40",
            "Article 4(1)-(2) and Article 14",
            "An ACFTA good not otherwise covered by a product-specific rule must meet "
            "regional value content of at least 40 percent and the claim is supported "
            "by the prescribed certificate of origin.",
        ),
        "rcep_roo_8703": (
            "rcep_psr",
            "CLAUSE-MY-RCEP-8703-RVC40",
            "Annex 3A, page 3A-145, heading 87.03",
            "RCEP heading 87.03 has a product-specific RVC40 rule.",
        ),
        "rcep_current": (
            "rcep_amend_2026",
            "CLAUSE-MY-RCEP-CURRENT-2026",
            "Citation and commencement; Second Schedule amendments",
            "The 2026 amendment comes into operation on 31 March 2026; current vehicle "
            "rates are retained from the official JKDM HS Explorer current-rate view.",
        ),
        "import_control": (
            "prohibition_2023",
            "CLAUSE-MY-PUA117-IMPORT-CONTROL-SCREEN",
            "Paragraph 4 and applicable schedules, subject to amendments",
            "Goods listed in the conditional prohibition schedules require the stated "
            "licence or approval; every exact line in a parts route must be screened.",
        ),
        "no_vat": (
            "mysst_faq",
            "CLAUSE-MY-SST-SINGLE-STAGE-NO-VAT",
            "MySST overview and Sales Tax FAQ",
            "Malaysia applies single-stage sales tax to taxable imported and locally "
            "manufactured goods; a separate VAT or GST is not added to the vehicle-goods "
            "tax chain.",
        ),
    }
    return {
        key: upsert_clause(
            session,
            clause_code=clause_code,
            source_document_id=source_ids[source_key],
            locator_type="LEGAL_OR_POLICY_LOCATOR",
            locator_value=locator,
            summary=summary,
        )
        for key, (source_key, clause_code, locator, summary) in clause_specs.items()
    }


def cbu_dsl(scenario_code: str) -> dict[str, Any]:
    inputs = [
        {
            "path": "vehicle.customs_value",
            "type": "currency",
            "required": True,
            "ownership": "ENTERPRISE",
        },
        {
            "path": "vehicle.pdk_tariff_code",
            "type": "string",
            "required": True,
            "ownership": "MIXED",
        },
        {
            "path": "rate.import_duty",
            "type": "decimal",
            "required": True,
            "ownership": "PUBLIC",
        },
        {
            "path": "rate.excise",
            "type": "decimal",
            "required": True,
            "ownership": "PUBLIC",
        },
        {
            "path": "rate.sst",
            "type": "decimal",
            "required": True,
            "ownership": "PUBLIC",
        },
        {
            "path": "approval.import_ap_confirmed",
            "type": "boolean",
            "required": True,
            "ownership": "ENTERPRISE",
        },
        {
            "path": "origin.preference_eligible",
            "type": "boolean",
            "required": True,
            "ownership": "ENTERPRISE",
        },
    ]
    import_duty = {
        "op": "MULTIPLY",
        "args": [{"ref": "vehicle.customs_value"}, {"ref": "rate.import_duty"}],
    }
    excise_base = {
        "op": "ADD",
        "args": [{"ref": "vehicle.customs_value"}, {"ref": "tax.import_duty"}],
    }
    excise = {
        "op": "MULTIPLY",
        "args": [excise_base, {"ref": "rate.excise"}],
    }
    sst_base = {
        "op": "ADD",
        "args": [
            {"ref": "vehicle.customs_value"},
            {"ref": "tax.import_duty"},
            {"ref": "tax.excise"},
        ],
    }
    sst = {
        "op": "MULTIPLY",
        "args": [sst_base, {"ref": "rate.sst"}],
    }
    total = {
        "op": "ADD",
        "args": [
            {"ref": "tax.import_duty"},
            {"ref": "tax.excise"},
            {"ref": "tax.sst"},
        ],
    }
    return {
        "dsl_version": "0.1.0",
        "scenario_code": scenario_code,
        "inputs": inputs,
        "steps": [
            {
                "step_id": "IMPORT_DUTY",
                "sequence_no": 1,
                "tax_code": "IMPORT_DUTY",
                "base": {"ref": "vehicle.customs_value"},
                "rate_source": {
                    "type": "INPUT",
                    "reference": "rate.import_duty",
                },
                "amount": import_duty,
                "on_missing": "BLOCK",
                "display_formula": "customs value x selected MFN or eligible FTA rate",
            },
            {
                "step_id": "EXCISE",
                "sequence_no": 2,
                "tax_code": "EXCISE",
                "depends_on": ["IMPORT_DUTY"],
                "base": excise_base,
                "rate_source": {"type": "INPUT", "reference": "rate.excise"},
                "amount": excise,
                "on_missing": "BLOCK",
                "display_formula": "(customs value + import duty) x excise rate",
            },
            {
                "step_id": "SST",
                "sequence_no": 3,
                "tax_code": "SST",
                "depends_on": ["IMPORT_DUTY", "EXCISE"],
                "base": sst_base,
                "rate_source": {"type": "INPUT", "reference": "rate.sst"},
                "amount": sst,
                "on_missing": "BLOCK",
                "display_formula": (
                    "(customs value + import duty + excise) x sales tax rate"
                ),
            },
        ],
        "outputs": [
            {"code": "TOTAL_TAX", "expression": total},
            {
                "code": "EFFECTIVE_TAX_RATE",
                "expression": {
                    "op": "DIVIDE",
                    "args": [total, {"ref": "vehicle.customs_value"}],
                },
            },
        ],
        "completeness_policy": {
            "unknown_rate": "BLOCK",
            "missing_required_input": "BLOCK",
            "failed_eligibility": "FALLBACK",
        },
    }


def local_finished_steps(start_sequence: int = 3) -> list[dict[str, Any]]:
    local_excise = {
        "op": "MULTIPLY",
        "args": [{"ref": "local.excise_value"}, {"ref": "rate.local_excise"}],
    }
    local_sst = {
        "op": "MULTIPLY",
        "args": [{"ref": "local.sales_tax_value"}, {"ref": "rate.local_sst"}],
    }
    return [
        {
            "step_id": "LOCAL_EXCISE",
            "sequence_no": start_sequence,
            "tax_code": "EXCISE",
            "base": {"ref": "local.excise_value"},
            "rate_source": {
                "type": "INPUT",
                "reference": "rate.local_excise",
            },
            "amount": local_excise,
            "on_missing": "BLOCK",
            "display_formula": (
                "approved local excise value x statutory or project-approved rate"
            ),
        },
        {
            "step_id": "LOCAL_SST",
            "sequence_no": start_sequence + 1,
            "tax_code": "SST",
            "base": {"ref": "local.sales_tax_value"},
            "rate_source": {"type": "INPUT", "reference": "rate.local_sst"},
            "amount": local_sst,
            "on_missing": "BLOCK",
            "display_formula": (
                "transaction or computed local sales value x selected sales tax rate"
            ),
        },
    ]


def local_inputs() -> list[dict[str, Any]]:
    return [
        {
            "path": "local.excise_value",
            "type": "currency",
            "required": True,
            "ownership": "ENTERPRISE",
        },
        {
            "path": "rate.local_excise",
            "type": "decimal",
            "required": True,
            "ownership": "MIXED",
        },
        {
            "path": "local.sales_tax_value",
            "type": "currency",
            "required": True,
            "ownership": "ENTERPRISE",
        },
        {
            "path": "rate.local_sst",
            "type": "decimal",
            "required": True,
            "ownership": "MIXED",
        },
        {
            "path": "approval.local_assembly_confirmed",
            "type": "boolean",
            "required": True,
            "ownership": "ENTERPRISE",
        },
        {
            "path": "approval.project_incentive_confirmed",
            "type": "boolean",
            "required": True,
            "ownership": "ENTERPRISE",
        },
    ]


def ckd_whole_kit_dsl(scenario_code: str) -> dict[str, Any]:
    inputs = [
        {
            "path": "import.customs_value",
            "type": "currency",
            "required": True,
            "ownership": "ENTERPRISE",
        },
        {
            "path": "rate.import_duty",
            "type": "decimal",
            "required": True,
            "ownership": "PUBLIC",
        },
        {
            "path": "approval.miti_ckd_ap_confirmed",
            "type": "boolean",
            "required": True,
            "ownership": "ENTERPRISE",
        },
        {
            "path": "classification.ckd_definition_confirmed",
            "type": "boolean",
            "required": True,
            "ownership": "MIXED",
        },
        *local_inputs(),
    ]
    steps = [
        {
            "step_id": "KIT_IMPORT_DUTY",
            "sequence_no": 1,
            "tax_code": "IMPORT_DUTY",
            "base": {"ref": "import.customs_value"},
            "rate_source": {"type": "INPUT", "reference": "rate.import_duty"},
            "amount": {
                "op": "MULTIPLY",
                "args": [
                    {"ref": "import.customs_value"},
                    {"ref": "rate.import_duty"},
                ],
            },
            "on_missing": "BLOCK",
            "display_formula": "CKD kit customs value x exact CKD tariff rate",
        },
        {
            "step_id": "KIT_IMPORT_SST",
            "sequence_no": 2,
            "tax_code": "SST",
            "depends_on": ["KIT_IMPORT_DUTY"],
            "base": {
                "op": "ADD",
                "args": [
                    {"ref": "import.customs_value"},
                    {"ref": "tax.kit_import_duty"},
                ],
            },
            "rate_source": {"type": "CONSTANT", "value": 0},
            "amount": {"number": 0},
            "on_missing": "BLOCK",
            "display_formula": "0 under P.U. (A) 171/2025 exact CKD line",
        },
        *local_finished_steps(3),
    ]
    total = {
        "op": "ADD",
        "args": [
            {"ref": "tax.kit_import_duty"},
            {"ref": "tax.kit_import_sst"},
            {"ref": "tax.local_excise"},
            {"ref": "tax.local_sst"},
        ],
    }
    return {
        "dsl_version": "0.1.0",
        "scenario_code": scenario_code,
        "inputs": inputs,
        "steps": steps,
        "outputs": [
            {"code": "TOTAL_TAX", "expression": total},
            {
                "code": "EFFECTIVE_TAX_RATE",
                "expression": {
                    "op": "DIVIDE",
                    "args": [total, {"ref": "import.customs_value"}],
                },
            },
        ],
        "fallback_scenario_code": "SCN-MY-ROUTE-03-PARTS-SUBASSEMBLIES",
        "completeness_policy": {
            "unknown_rate": "BLOCK",
            "missing_required_input": "BLOCK",
            "failed_eligibility": "FALLBACK",
        },
    }


def bucket_route_dsl(
    scenario_code: str, fallback_scenario_code: str | None
) -> dict[str, Any]:
    inputs = [
        {
            "path": "import.customs_value_total",
            "type": "currency",
            "required": True,
            "ownership": "ENTERPRISE",
        },
        {
            "path": "rate.weighted_import_duty",
            "type": "decimal",
            "required": True,
            "ownership": "MIXED",
        },
        {
            "path": "import.component_excise_total",
            "type": "currency",
            "required": True,
            "ownership": "MIXED",
        },
        {
            "path": "import.sales_tax_base_total",
            "type": "currency",
            "required": True,
            "ownership": "MIXED",
        },
        {
            "path": "rate.weighted_import_sst",
            "type": "decimal",
            "required": True,
            "ownership": "MIXED",
        },
        {
            "path": "allocation.no_double_count_confirmed",
            "type": "boolean",
            "required": True,
            "ownership": "ENTERPRISE",
        },
        *local_inputs(),
    ]
    steps = [
        {
            "step_id": "BUCKET_IMPORT_DUTY",
            "sequence_no": 1,
            "tax_code": "IMPORT_DUTY",
            "base": {"ref": "import.customs_value_total"},
            "rate_source": {
                "type": "INPUT",
                "reference": "rate.weighted_import_duty",
            },
            "amount": {
                "op": "MULTIPLY",
                "args": [
                    {"ref": "import.customs_value_total"},
                    {"ref": "rate.weighted_import_duty"},
                ],
            },
            "on_missing": "BLOCK",
            "display_formula": (
                "sum(value by mapped tax bucket x applicable duty rate)"
            ),
        },
        {
            "step_id": "BUCKET_IMPORT_EXCISE",
            "sequence_no": 2,
            "tax_code": "EXCISE",
            "base": {"ref": "import.component_excise_total"},
            "rate_source": {"type": "CONSTANT", "value": 1},
            "amount": {"ref": "import.component_excise_total"},
            "on_missing": "BLOCK",
            "display_formula": (
                "sum of component-level excise, normally zero unless an exact line applies"
            ),
        },
        {
            "step_id": "BUCKET_IMPORT_SST",
            "sequence_no": 3,
            "tax_code": "SST",
            "base": {"ref": "import.sales_tax_base_total"},
            "rate_source": {
                "type": "INPUT",
                "reference": "rate.weighted_import_sst",
            },
            "amount": {
                "op": "MULTIPLY",
                "args": [
                    {"ref": "import.sales_tax_base_total"},
                    {"ref": "rate.weighted_import_sst"},
                ],
            },
            "on_missing": "BLOCK",
            "display_formula": (
                "sum of each bucket sales-tax base x its exact sales-tax rate"
            ),
        },
        *local_finished_steps(4),
    ]
    total = {
        "op": "ADD",
        "args": [
            {"ref": "tax.bucket_import_duty"},
            {"ref": "tax.bucket_import_excise"},
            {"ref": "tax.bucket_import_sst"},
            {"ref": "tax.local_excise"},
            {"ref": "tax.local_sst"},
        ],
    }
    result: dict[str, Any] = {
        "dsl_version": "0.1.0",
        "scenario_code": scenario_code,
        "inputs": inputs,
        "steps": steps,
        "outputs": [
            {"code": "TOTAL_TAX", "expression": total},
            {
                "code": "EFFECTIVE_TAX_RATE",
                "expression": {
                    "op": "DIVIDE",
                    "args": [total, {"ref": "import.customs_value_total"}],
                },
            },
        ],
        "completeness_policy": {
            "unknown_rate": "BLOCK",
            "missing_required_input": "BLOCK",
            "failed_eligibility": "FALLBACK",
        },
    }
    if fallback_scenario_code:
        result["fallback_scenario_code"] = fallback_scenario_code
    return result


def local_only_dsl(scenario_code: str) -> dict[str, Any]:
    steps = local_finished_steps(1)
    total = {
        "op": "ADD",
        "args": [{"ref": "tax.local_excise"}, {"ref": "tax.local_sst"}],
    }
    return {
        "dsl_version": "0.1.0",
        "scenario_code": scenario_code,
        "inputs": local_inputs(),
        "steps": steps,
        "outputs": [{"code": "TOTAL_TAX", "expression": total}],
        "completeness_policy": {
            "unknown_rate": "BLOCK",
            "missing_required_input": "BLOCK",
            "failed_eligibility": "FALLBACK",
        },
    }


def seed_routes(session: Session, clauses: dict[str, str]) -> dict[str, str]:
    routes = [
        {
            "code": ROUTE_CBU,
            "order": 1,
            "name_cn": "CBU整车进口",
            "name_en": "Completely Built-Up Vehicle Import",
            "kind": "CBU",
            "mode": "CBU",
            "granularity": "FINISHED_VEHICLE",
            "condition": {
                "all": [
                    {
                        "field": "vehicle.assembled_outside_malaysia",
                        "operator": "EQ",
                        "value": True,
                    },
                    {
                        "field": "shipment.finished_vehicle",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            "required": [
                "vehicle.pdk_tariff_code",
                "vehicle.customs_value",
                "vehicle.powertrain",
                "vehicle.body_type",
                "vehicle.drive_type",
                "vehicle.displacement_cc_if_applicable",
                "origin.country_iso2",
                "origin.preference_evidence_if_claimed",
                "approval.import_ap",
                "approval.annual_ap_allocation",
            ],
            "dsl": cbu_dsl("SCN-MY-ROUTE-01-CBU"),
            "fallback": None,
            "note": (
                "Use one exact finished-vehicle line. Do not split a CBU vehicle into "
                "parts for tax calculation."
            ),
            "status": "VERIFIED",
        },
        {
            "code": ROUTE_CKD,
            "order": 2,
            "name_cn": "整套CKD车辆税号进口＋本地组装",
            "name_en": "Whole CKD Kit Vehicle Line plus Local Assembly",
            "kind": "CKD_WHOLE_KIT",
            "mode": "CKD",
            "granularity": "CKD_VEHICLE_TARIFF_LINE",
            "condition": {
                "all": [
                    {
                        "field": "approval.miti_ckd_ap_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                    {
                        "field": "classification.ckd_definition_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                    {
                        "field": "shipment.complete_ckd_kit",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            "required": [
                "vehicle.ckd_pdk_tariff_code",
                "import.ckd_kit_customs_value",
                "classification.ckd_definition_confirmation",
                "approval.miti_ckd_ap",
                "approval.local_assembly_model",
                "origin.preference_evidence_if_claimed",
                "local.excise_value",
                "local.sales_tax_value",
                "approval.project_tax_benefit",
            ],
            "dsl": ckd_whole_kit_dsl("SCN-MY-ROUTE-02-CKD-WHOLE-KIT"),
            "fallback": ROUTE_SUBASSEMBLIES,
            "note": (
                "Only use this route after CKD legal-definition and AP confirmation. "
                "Failure falls to N205 Parts/Sub-Assemblies, not to a guessed CKD rate."
            ),
            "status": "VERIFIED",
        },
        {
            "code": ROUTE_SUBASSEMBLIES,
            "order": 3,
            "name_cn": "分总成/税务桶进口＋本地组装",
            "name_en": "Parts and Sub-Assemblies Tax Buckets plus Local Assembly",
            "kind": "PARTS_SUBASSEMBLIES",
            "mode": "PARTS",
            "granularity": "SUBASSEMBLY_TAX_BUCKET",
            "condition": {
                "all": [
                    {
                        "field": "approval.local_assembly_model_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                    {
                        "field": "approval.n205_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                    {
                        "field": "classification.ckd_definition_confirmed",
                        "operator": "EQ",
                        "value": False,
                    },
                ]
            },
            "required": [
                "approval.n205",
                "shipment.subassembly_manifest",
                "bucket.customs_values",
                "bucket.ccu_mappings",
                "bucket.origin_evidence",
                "bucket.import_control_results",
                "local.excise_value",
                "local.sales_tax_value",
                "approval.project_tax_benefit",
            ],
            "dsl": bucket_route_dsl(
                "SCN-MY-ROUTE-03-PARTS-SUBASSEMBLIES",
                "SCN-MY-ROUTE-04-PART-LEVEL",
            ),
            "fallback": ROUTE_PART_LEVEL,
            "note": (
                "Calculate by a limited set of tax buckets and high-value exceptions. "
                "Do not assume unlisted parts are duty-free."
            ),
            "status": "VERIFIED",
        },
        {
            "code": ROUTE_PART_LEVEL,
            "order": 4,
            "name_cn": "海关归类单元/零件级进口＋本地组装",
            "name_en": "Customs Classification Unit or Part-Level Import",
            "kind": "PART_LEVEL",
            "mode": "PARTS",
            "granularity": "CUSTOMS_CLASSIFICATION_UNIT",
            "condition": {
                "all": [
                    {
                        "field": "shipment.whole_ckd_route_available",
                        "operator": "EQ",
                        "value": False,
                    },
                    {
                        "field": "shipment.stable_subassembly_bucket_available",
                        "operator": "EQ",
                        "value": False,
                    },
                ]
            },
            "required": [
                "shipment.ccu_manifest",
                "ccu.required_technical_parameters",
                "ccu.pdk_mappings",
                "ccu.origin_evidence",
                "ccu.import_control_results",
                "local.excise_value",
                "local.sales_tax_value",
                "approval.project_tax_benefit",
            ],
            "dsl": bucket_route_dsl("SCN-MY-ROUTE-04-PART-LEVEL", None),
            "fallback": None,
            "note": (
                "The calculation grain is CCU, not every enterprise physical part "
                "number. Candidate classifications remain blocked until required "
                "technical parameters are supplied."
            ),
            "status": "CANDIDATE",
        },
        {
            "code": ROUTE_MIXED,
            "order": 5,
            "name_cn": "混合KD路线",
            "name_en": "Mixed KD Route",
            "kind": "MIXED_KD",
            "mode": "PARTS",
            "granularity": "MIXED_ROUTE_ALLOCATION",
            "condition": {
                "all": [
                    {
                        "field": "shipment.multiple_import_routes",
                        "operator": "EQ",
                        "value": True,
                    },
                    {
                        "field": "allocation.no_double_count_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            "required": [
                "allocation.route_by_manifest_line",
                "allocation.unique_double_count_key",
                "allocation.local_purchase_exclusion",
                "allocation.approval_by_route",
                "allocation.origin_evidence_by_route",
                "local.excise_value",
                "local.sales_tax_value",
                "approval.project_tax_benefit",
            ],
            "dsl": bucket_route_dsl("SCN-MY-ROUTE-05-MIXED-KD", None),
            "fallback": None,
            "note": (
                "Sum each import bucket once and levy finished-vehicle excise and sales "
                "tax once. Local purchases do not enter the import-duty denominator."
            ),
            "status": "CANDIDATE",
        },
    ]
    sql = text(
        """
        INSERT INTO rules.vehicle_tax_route (
          route_code, country_id, decision_order, route_name_cn, route_name_en,
          route_kind, import_mode, classification_granularity,
          decision_condition, required_input_fields, calculation_dsl,
          fallback_route_code, decision_note, effective_from, version,
          record_status, verification_status
        )
        SELECT
          :code, country.country_id, :decision_order, :name_cn, :name_en,
          :kind, CAST(:mode AS ref.import_mode), :granularity,
          CAST(:condition AS jsonb), CAST(:required AS jsonb), CAST(:dsl AS jsonb),
          :fallback, :note, DATE '2025-11-01', 1, 'ACTIVE',
          CAST(:status AS ref.verification_status)
        FROM ref.country country
        WHERE country.iso2 = 'MY'
        ON CONFLICT (route_code, version) DO UPDATE SET
          decision_order = EXCLUDED.decision_order,
          route_name_cn = EXCLUDED.route_name_cn,
          route_name_en = EXCLUDED.route_name_en,
          route_kind = EXCLUDED.route_kind,
          import_mode = EXCLUDED.import_mode,
          classification_granularity = EXCLUDED.classification_granularity,
          decision_condition = EXCLUDED.decision_condition,
          required_input_fields = EXCLUDED.required_input_fields,
          calculation_dsl = EXCLUDED.calculation_dsl,
          fallback_route_code = EXCLUDED.fallback_route_code,
          decision_note = EXCLUDED.decision_note,
          record_status = 'ACTIVE',
          verification_status = EXCLUDED.verification_status,
          updated_at = now()
        RETURNING vehicle_tax_route_id
        """
    )
    route_ids: dict[str, str] = {}
    for item in routes:
        route_ids[item["code"]] = str(
            session.execute(
                sql,
                {
                    **item,
                    "decision_order": item["order"],
                    "condition": json_text(item["condition"]),
                    "required": json_text(item["required"]),
                    "dsl": json_text(item["dsl"]),
                },
            ).scalar_one()
        )

    source_links = {
        ROUTE_CBU: [
            ("n180_ap", "CBU AP and model/quota route"),
            ("cbu_tax_sequence", "Imported CBU tax sequence"),
            ("excise_8703", "Statutory excise line"),
        ],
        ROUTE_CKD: [
            ("ckd_route", "Legal CKD versus N205 split"),
            ("ckd_sst_exempt", "Exact CKD sales-tax exemption"),
            ("local_excise_payment", "Locally manufactured vehicle excise"),
            ("local_vehicle_sst", "Locally assembled finished-vehicle sales tax"),
        ],
        ROUTE_SUBASSEMBLIES: [
            ("ckd_route", "Fallback from CKD legal definition"),
            ("n205_ap", "N205 AP requirements"),
            ("import_control", "Exact-line import-control screening"),
        ],
        ROUTE_PART_LEVEL: [
            ("import_control", "Exact-line import-control screening"),
            ("component_exemption", "Approval-gated component exemption"),
        ],
        ROUTE_MIXED: [
            ("ckd_route", "Underlying CKD and N205 routes"),
            ("import_control", "Underlying exact-line import controls"),
            ("local_excise_payment", "Finished vehicle taxed once"),
        ],
    }
    link_sql = text(
        """
        INSERT INTO rules.vehicle_tax_route_source_link (
          vehicle_tax_route_id, source_clause_id, source_purpose, sequence_no
        ) VALUES (
          CAST(:route_id AS uuid), CAST(:clause_id AS uuid), :purpose, :sequence_no
        )
        ON CONFLICT (vehicle_tax_route_id, source_clause_id) DO UPDATE SET
          source_purpose = EXCLUDED.source_purpose,
          sequence_no = EXCLUDED.sequence_no
        """
    )
    for route_code, links in source_links.items():
        for sequence_no, (clause_key, purpose) in enumerate(links, start=1):
            session.execute(
                link_sql,
                {
                    "route_id": route_ids[route_code],
                    "clause_id": clauses[clause_key],
                    "purpose": purpose,
                    "sequence_no": sequence_no,
                },
            )
    return route_ids


def seed_buckets(session: Session, clauses: dict[str, str]) -> None:
    buckets = [
        (
            "BUCKET-MY-CKD-WHOLE-KIT",
            "整套CKD车辆税号",
            "Whole CKD Vehicle Kit",
            [ROUTE_CKD, ROUTE_MIXED],
            ["Goods accepted under an exact 8703 CKD national tariff line"],
            ["Loose parts outside the accepted CKD presentation"],
            "CKD_VEHICLE_TARIFF_LINE",
            {
                "duty": "EXACT_CKD_LINE_MFN_OR_ELIGIBLE_FTA",
                "sales_tax": "EXEMPT_PUA171",
                "excise": "NOT_AT_KIT_IMPORT",
            },
            {"apply_finished_vehicle_excise_and_sst_once": True},
            [
                "ckd_tariff_code",
                "customs_value",
                "origin_preference_evidence",
                "miti_ckd_ap",
            ],
            "shipment_line_id",
            "ckd_sst_exempt",
            "VERIFIED",
        ),
        (
            "BUCKET-MY-ICE-POWERTRAIN",
            "发动机与变速箱",
            "Engine and Transmission",
            [ROUTE_SUBASSEMBLIES, ROUTE_PART_LEVEL, ROUTE_MIXED],
            ["Engine", "transmission", "fitted engine or powertrain subassembly"],
            ["EV traction battery, traction motor and power electronics"],
            "CCU_OR_SUBASSEMBLY",
            {
                "duty": "EXACT_PDK_OR_ELIGIBLE_FTA_BY_CCU",
                "sales_tax": "EXACT_PDK_LINE",
                "exemption": "ONLY_IF_APPROVAL_COVERS_LINE",
            },
            {"included_in_local_valuation": True},
            [
                "ccu_mapping",
                "customs_value",
                "technical_specification",
                "origin_evidence",
            ],
            "manifest_line_or_ccu_allocation_id",
            "import_control",
            "VERIFIED",
        ),
        (
            "BUCKET-MY-EV-POWERTRAIN",
            "电池、电机与电控",
            "Battery, Motor and Power Electronics",
            [ROUTE_SUBASSEMBLIES, ROUTE_PART_LEVEL, ROUTE_MIXED],
            ["Traction battery", "traction motor", "inverter", "on-board charger"],
            ["12V starter battery unless separately mapped"],
            "CCU_OR_SUBASSEMBLY",
            {
                "duty": "EXACT_PDK_OR_ELIGIBLE_FTA_BY_CCU",
                "sales_tax": "EXACT_PDK_LINE",
                "exemption": "LOCAL_BEV_COMPONENT_APPROVAL_ONLY",
            },
            {"included_in_local_valuation": True},
            [
                "ccu_mapping",
                "customs_value",
                "technical_specification",
                "origin_evidence",
                "ev_component_exemption_approval",
            ],
            "manifest_line_or_ccu_allocation_id",
            "local_bev_2027",
            "VERIFIED",
        ),
        (
            "BUCKET-MY-BODY-CHASSIS",
            "车身与底盘结构件",
            "Body and Chassis Structures",
            [ROUTE_SUBASSEMBLIES, ROUTE_PART_LEVEL, ROUTE_MIXED],
            ["Body shell", "body-in-white", "chassis and major structural assemblies"],
            ["Finished vehicle accepted as CBU or whole CKD kit"],
            "CCU_OR_SUBASSEMBLY",
            {
                "duty": "EXACT_PDK_OR_ELIGIBLE_FTA_BY_CCU",
                "sales_tax": "EXACT_PDK_LINE",
                "gri_2a": "SCREEN_COMPLETE_OR_INCOMPLETE_VEHICLE_RISK",
            },
            {"included_in_local_valuation": True},
            [
                "assembly_state",
                "included_components",
                "customs_value",
                "ccu_mapping",
            ],
            "manifest_line_or_ccu_allocation_id",
            "import_control",
            "CANDIDATE",
        ),
        (
            "BUCKET-MY-COMMON-IMPORT-PARTS",
            "普通进口零部件",
            "Common Imported Parts",
            [ROUTE_SUBASSEMBLIES, ROUTE_PART_LEVEL, ROUTE_MIXED],
            ["Stable CCUs sharing confirmed tax treatment"],
            ["High-value, disputed, controlled or trade-remedy lines"],
            "CCU",
            {
                "duty": "WEIGHTED_EXACT_CCU_LINES",
                "sales_tax": "WEIGHTED_EXACT_CCU_LINES",
                "zero_rate": "NEVER_ASSUMED",
            },
            {"included_in_local_valuation": True},
            ["ccu_code", "customs_value", "tariff_mapping", "origin_evidence"],
            "manifest_line_or_ccu_allocation_id",
            "import_control",
            "VERIFIED",
        ),
        (
            "BUCKET-MY-APPROVED-EXEMPT-IMPORTS",
            "获批免税进口件",
            "Approved Exempt Imports",
            [ROUTE_SUBASSEMBLIES, ROUTE_PART_LEVEL, ROUTE_MIXED],
            ["Only tariff lines and quantities covered by a valid exemption approval"],
            ["Pending applications or items outside the approved schedule"],
            "APPROVAL_LINE",
            {
                "duty": "APPROVED_RATE_ONLY",
                "sales_tax": "APPROVED_RATE_ONLY",
                "fallback": "STATUTORY_RATE",
            },
            {"included_in_local_valuation": True},
            [
                "approval_reference",
                "approved_line",
                "approved_quantity_or_value",
                "validity_dates",
            ],
            "approval_reference_plus_manifest_line",
            "component_exemption",
            "VERIFIED",
        ),
        (
            "BUCKET-MY-LOCAL-PURCHASE",
            "本地采购件",
            "Local Purchases",
            [ROUTE_SUBASSEMBLIES, ROUTE_PART_LEVEL, ROUTE_MIXED],
            ["Components purchased in Malaysia and not imported by the project"],
            ["Imported components routed through a local intermediary without proof"],
            "LOCAL_COST_LINE",
            {
                "import_duty": "NOT_APPLICABLE",
                "import_sales_tax": "NOT_IN_IMPORT_BUCKET",
            },
            {"included_in_local_valuation": True},
            ["supplier", "local_invoice", "country_of_supply", "cost"],
            "local_purchase_line_id",
            None,
            "VERIFIED",
        ),
        (
            "BUCKET-MY-SPECIAL-CONTROLLED",
            "特殊监管与贸易救济件",
            "Special Controlled or Trade-Remedy Parts",
            [ROUTE_SUBASSEMBLIES, ROUTE_PART_LEVEL, ROUTE_MIXED],
            ["Tyres", "glass", "steel", "batteries and any controlled exact line"],
            ["Items already cleared as ordinary parts without a current control"],
            "EXACT_NATIONAL_TARIFF_LINE",
            {
                "duty": "EXACT_LINE_PLUS_ADDITIONAL_MEASURES",
                "permit": "MANDATORY_IF_LISTED",
                "trade_remedy": "SCREEN_AT_CALCULATION_DATE",
            },
            {"included_in_local_valuation": True},
            [
                "national_tariff_code",
                "origin_country",
                "manufacturer",
                "permit",
                "trade_remedy_screen",
            ],
            "manifest_line_id",
            "import_control",
            "CANDIDATE",
        ),
    ]
    sql = text(
        """
        INSERT INTO rules.kd_tax_bucket_definition (
          bucket_code, country_id, bucket_name_cn, bucket_name_en,
          applicable_route_codes, included_scope, excluded_scope,
          classification_granularity, import_tax_treatment,
          local_finished_vehicle_treatment, required_input_fields,
          double_count_key, source_clause_id, effective_from, version,
          record_status, verification_status
        )
        SELECT
          :code, country.country_id, :name_cn, :name_en,
          CAST(:routes AS jsonb), CAST(:included AS jsonb), CAST(:excluded AS jsonb),
          :granularity, CAST(:import_treatment AS jsonb),
          CAST(:local_treatment AS jsonb), CAST(:required AS jsonb),
          :double_count_key,
          CASE WHEN CAST(:source_clause_id AS text) IS NULL THEN NULL
               ELSE CAST(:source_clause_id AS uuid) END,
          DATE '2025-11-01', 1, 'ACTIVE',
          CAST(:status AS ref.verification_status)
        FROM ref.country country
        WHERE country.iso2 = 'MY'
        ON CONFLICT (bucket_code, version) DO UPDATE SET
          bucket_name_cn = EXCLUDED.bucket_name_cn,
          bucket_name_en = EXCLUDED.bucket_name_en,
          applicable_route_codes = EXCLUDED.applicable_route_codes,
          included_scope = EXCLUDED.included_scope,
          excluded_scope = EXCLUDED.excluded_scope,
          classification_granularity = EXCLUDED.classification_granularity,
          import_tax_treatment = EXCLUDED.import_tax_treatment,
          local_finished_vehicle_treatment =
            EXCLUDED.local_finished_vehicle_treatment,
          required_input_fields = EXCLUDED.required_input_fields,
          double_count_key = EXCLUDED.double_count_key,
          source_clause_id = EXCLUDED.source_clause_id,
          record_status = 'ACTIVE',
          verification_status = EXCLUDED.verification_status,
          updated_at = now()
        """
    )
    for (
        code,
        name_cn,
        name_en,
        routes,
        included,
        excluded,
        granularity,
        import_treatment,
        local_treatment,
        required,
        double_count_key,
        clause_key,
        status,
    ) in buckets:
        session.execute(
            sql,
            {
                "code": code,
                "name_cn": name_cn,
                "name_en": name_en,
                "routes": json_text(routes),
                "included": json_text(included),
                "excluded": json_text(excluded),
                "granularity": granularity,
                "import_treatment": json_text(import_treatment),
                "local_treatment": json_text(local_treatment),
                "required": json_text(required),
                "double_count_key": double_count_key,
                "source_clause_id": clauses[clause_key] if clause_key else None,
                "status": status,
            },
        )


def ckd_codes_from_order() -> set[str]:
    pdf_path = (
        EVIDENCE_2029 / "MY_Sales_Tax_Goods_Exempted_Order_2025_PUA171.pdf"
    )
    content = "\n".join(
        page.extract_text() or "" for page in PdfReader(pdf_path).pages
    )
    matches = re.findall(
        r"8703[.\s]*([0-9]{2})[.\s]*([0-9]{2})[.\s]*([0-9]{2})",
        content,
    )
    codes = {"8703" + "".join(groups) for groups in matches}
    if len(codes) != 167:
        raise AssertionError(
            f"Expected 167 official 8703 CKD exempt lines, found {len(codes)}"
        )
    return codes


def seed_tariff_source_clauses(session: Session) -> dict[tuple[str, str], str]:
    clauses: dict[tuple[str, str], str] = {}
    for hs6 in VEHICLE_HS6:
        pdk_file = EVIDENCE_2029 / f"JKDM_HS_Explorer_PDK2025_{hs6}.html"
        source_id = upsert_source(
            session,
            source_code=f"SRC-MY-JKDM-PDK2025-VEHICLE-{hs6}",
            authority_code="MY-JKDM",
            title=f"JKDM HS Explorer PDK 2025 vehicle query {hs6}",
            document_number="P.U. (A) 384/2025",
            source_type="OFFICIAL_PORTAL",
            canonical_url="https://ezhs.customs.gov.my/",
            publication_date=None,
            effective_from=date(2025, 11, 1),
            effective_to=None,
            file_path=pdk_file,
        )
        clauses[("MFN", hs6)] = upsert_clause(
            session,
            clause_code=f"CLAUSE-MY-JKDM-PDK2025-VEHICLE-{hs6}",
            source_document_id=source_id,
            locator_type="HS_EXPLORER_QUERY",
            locator_value=f"PDK 2025; HS Code {hs6}",
            summary=(
                f"Official PDK 2025 exact national lines under {hs6}, including "
                "import duty, sales tax and displayed excise columns."
            ),
        )
        for regime in ("ACFTA", "RCEP"):
            fta_file = (
                EVIDENCE_2029
                / f"JKDM_HS_Explorer_{regime}_{hs6}_RATE_2026.html"
            )
            source_id = upsert_source(
                session,
                source_code=f"SRC-MY-JKDM-{regime}-2026-VEHICLE-{hs6}",
                authority_code="MY-JKDM",
                title=(
                    f"JKDM HS Explorer {regime} current-rate vehicle query {hs6}"
                ),
                document_number=(
                    "P.U. (A) 454/2024"
                    if regime == "ACFTA"
                    else "P.U. (A) 426/2025 as amended by P.U. (A) 127/2026"
                ),
                source_type="OFFICIAL_PORTAL",
                canonical_url="https://ezhs.customs.gov.my/",
                publication_date=None,
                effective_from=(
                    date(2025, 1, 1)
                    if regime == "ACFTA"
                    else date(2026, 3, 31)
                ),
                effective_to=None,
                file_path=fta_file,
            )
            clauses[(regime, hs6)] = upsert_clause(
                session,
                clause_code=f"CLAUSE-MY-JKDM-{regime}-2026-VEHICLE-{hs6}",
                source_document_id=source_id,
                locator_type="HS_EXPLORER_QUERY",
                locator_value=f"{regime}; HS Code {hs6}; RATE_2026",
                summary=(
                    f"Official {regime} current-rate exact national lines under "
                    f"{hs6}, captured from JKDM HS Explorer."
                ),
            )
    return clauses


def classify_fta_route(
    code: str, ckd_codes: set[str], cbu_codes: set[str]
) -> tuple[str, str | None]:
    if code in ckd_codes:
        return ROUTE_CKD, code
    if code in cbu_codes:
        return ROUTE_CBU, code
    ckd_prefix = [item for item in ckd_codes if item[:7] == code[:7]]
    cbu_prefix = [item for item in cbu_codes if item[:7] == code[:7]]
    if ckd_prefix and not cbu_prefix:
        return ROUTE_CKD, None
    if cbu_prefix and not ckd_prefix:
        return ROUTE_CBU, None
    raise AssertionError(f"Unable to determine CBU/CKD route for FTA line {code}")


def seed_vehicle_tariff_rates(
    session: Session,
    route_ids: dict[str, str],
    clauses: dict[str, str],
) -> dict[str, int]:
    tariff_clauses = seed_tariff_source_clauses(session)
    ckd_codes = ckd_codes_from_order()
    pdk_rows: list[dict[str, str]] = []
    with PDK_EXTRACT.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["hs6_query"] in VEHICLE_HS6:
                pdk_rows.append(row)
    pdk_codes = {row["national_tariff_code"] for row in pdk_rows}
    cbu_codes = pdk_codes - ckd_codes
    if len(pdk_rows) != 471 or len(cbu_codes) != 304:
        raise AssertionError(
            f"PDK vehicle coverage mismatch: rows={len(pdk_rows)}, "
            f"CBU={len(cbu_codes)}, CKD={len(ckd_codes)}"
        )

    agreement_ids = {
        row["agreement_code"]: str(row["trade_agreement_id"])
        for row in session.execute(
            text(
                """
                SELECT agreement_code, trade_agreement_id
                FROM ref.trade_agreement
                WHERE agreement_code IN ('ACFTA', 'RCEP')
                """
            )
        ).mappings()
    }
    insert_sql = text(
        """
        INSERT INTO customs.vehicle_tariff_rate_line (
          rate_line_code, country_id, vehicle_tax_route_id,
          tariff_schedule_code, tariff_year, origin_regime,
          trade_agreement_id, hs6_code, national_tariff_code,
          linked_pdk_tariff_code, tariff_description, powertrain,
          import_duty_rate, sales_tax_rate, excise_duty_rate,
          sales_tax_treatment, excise_treatment, eligibility_condition,
          tariff_source_clause_id, tax_treatment_source_clause_id,
          effective_from, version, record_status, verification_status,
          route_verification_status
        )
        SELECT
          :rate_line_code, country.country_id, CAST(:route_id AS uuid),
          :schedule, :tariff_year, CAST(:origin_regime AS ref.origin_regime),
          CASE WHEN CAST(:agreement_id AS text) IS NULL THEN NULL
               ELSE CAST(:agreement_id AS uuid) END,
          :hs6, :national_code, :linked_pdk_code, :description,
          CAST(:powertrain AS ref.powertrain), :import_rate, :sst_rate,
          :excise_rate, :sst_treatment, :excise_treatment,
          CAST(:eligibility AS jsonb), CAST(:tariff_clause_id AS uuid),
          CASE WHEN CAST(:tax_clause_id AS text) IS NULL THEN NULL
               ELSE CAST(:tax_clause_id AS uuid) END,
          :effective_from, 1, 'ACTIVE',
          CAST(:verification_status AS ref.verification_status),
          CAST(:route_status AS ref.verification_status)
        FROM ref.country country
        WHERE country.iso2 = 'MY'
        ON CONFLICT (rate_line_code, version) DO UPDATE SET
          vehicle_tax_route_id = EXCLUDED.vehicle_tax_route_id,
          tariff_schedule_code = EXCLUDED.tariff_schedule_code,
          tariff_year = EXCLUDED.tariff_year,
          origin_regime = EXCLUDED.origin_regime,
          trade_agreement_id = EXCLUDED.trade_agreement_id,
          linked_pdk_tariff_code = EXCLUDED.linked_pdk_tariff_code,
          tariff_description = EXCLUDED.tariff_description,
          powertrain = EXCLUDED.powertrain,
          import_duty_rate = EXCLUDED.import_duty_rate,
          sales_tax_rate = EXCLUDED.sales_tax_rate,
          excise_duty_rate = EXCLUDED.excise_duty_rate,
          sales_tax_treatment = EXCLUDED.sales_tax_treatment,
          excise_treatment = EXCLUDED.excise_treatment,
          eligibility_condition = EXCLUDED.eligibility_condition,
          tariff_source_clause_id = EXCLUDED.tariff_source_clause_id,
          tax_treatment_source_clause_id =
            EXCLUDED.tax_treatment_source_clause_id,
          effective_from = EXCLUDED.effective_from,
          record_status = 'ACTIVE',
          verification_status = EXCLUDED.verification_status,
          route_verification_status = EXCLUDED.route_verification_status,
          updated_at = now()
        """
    )
    for row in pdk_rows:
        code = row["national_tariff_code"]
        hs6 = row["hs6_query"]
        is_ckd = code in ckd_codes
        excise_rate = parse_rate(row["excise"])
        session.execute(
            insert_sql,
            {
                "rate_line_code": f"VTRL-MY-PDK2025-{code}-MFN",
                "route_id": route_ids[ROUTE_CKD if is_ckd else ROUTE_CBU],
                "schedule": "PDK-2025",
                "tariff_year": 2025,
                "origin_regime": "MFN",
                "agreement_id": None,
                "hs6": hs6,
                "national_code": code,
                "linked_pdk_code": code,
                "description": row["description"],
                "powertrain": POWERTRAIN_BY_HS6[hs6],
                "import_rate": parse_rate(row["import_rate"]),
                "sst_rate": parse_rate(row["sst"]),
                "excise_rate": excise_rate,
                "sst_treatment": "EXEMPT" if is_ckd else "TAXABLE",
                "excise_treatment": (
                    "NOT_AT_IMPORT"
                    if is_ckd
                    else "STATUTORY_RATE"
                    if excise_rate is not None
                    else "UNKNOWN"
                ),
                "eligibility": json_text(
                    {"origin_regime": "MFN", "preference_proof_required": False}
                ),
                "tariff_clause_id": tariff_clauses[("MFN", hs6)],
                "tax_clause_id": (
                    clauses["ckd_sst_exempt"]
                    if is_ckd
                    else tariff_clauses[("MFN", hs6)]
                ),
                "effective_from": date(2025, 11, 1),
                "verification_status": (
                    "VERIFIED"
                    if is_ckd or excise_rate is not None
                    else "CANDIDATE"
                ),
                "route_status": "VERIFIED",
            },
        )

    fta_rows: list[dict[str, str]] = []
    with FTA_EXTRACT.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if (
                row["hs6_query"] in VEHICLE_HS6
                and len(row["national_tariff_code"]) == 10
                and row["regime"] in ("ACFTA", "RCEP")
            ):
                fta_rows.append(row)
    if len(fta_rows) != 1118:
        raise AssertionError(
            f"Expected 1118 exact ACFTA/RCEP 8703 rate lines, found {len(fta_rows)}"
        )
    for row in fta_rows:
        regime = row["regime"]
        code = row["national_tariff_code"]
        hs6 = row["hs6_query"]
        route_code, linked_pdk = classify_fta_route(code, ckd_codes, cbu_codes)
        is_ckd = route_code == ROUTE_CKD
        session.execute(
            insert_sql,
            {
                "rate_line_code": f"VTRL-MY-{regime}-2026-{code}",
                "route_id": route_ids[route_code],
                "schedule": f"{regime}-CURRENT-2026",
                "tariff_year": 2026,
                "origin_regime": "FTA",
                "agreement_id": agreement_ids[regime],
                "hs6": hs6,
                "national_code": code,
                "linked_pdk_code": linked_pdk,
                "description": row["description"],
                "powertrain": POWERTRAIN_BY_HS6[hs6],
                "import_rate": parse_rate(row["current_rate"]),
                "sst_rate": 0.0 if is_ckd else 0.10,
                "excise_rate": None,
                "sst_treatment": "EXEMPT" if is_ckd else "TAXABLE",
                "excise_treatment": (
                    "NOT_AT_IMPORT"
                    if is_ckd
                    else "REQUIRES_PDK_CORRELATION"
                ),
                "eligibility": json_text(
                    {
                        "origin_country_iso2": "CN",
                        "agreement": regime,
                        "rvc_minimum": 0.40,
                        "proof_of_origin": (
                            "FORM_E"
                            if regime == "ACFTA"
                            else "FORM_RCEP_OR_APPROVED_EXPORTER_DECLARATION"
                        ),
                        "direct_consignment_or_transit_evidence": True,
                        "shipment_specific_confirmation_required": True,
                        "fallback_if_not_eligible": "MFN",
                    }
                ),
                "tariff_clause_id": tariff_clauses[(regime, hs6)],
                "tax_clause_id": (
                    clauses["ckd_sst_exempt"]
                    if is_ckd
                    else tariff_clauses[("MFN", hs6)]
                ),
                "effective_from": (
                    date(2025, 1, 1)
                    if regime == "ACFTA"
                    else date(2026, 3, 31)
                ),
                "verification_status": "VERIFIED",
                "route_status": "VERIFIED",
            },
        )
    return {
        "mfn_total": len(pdk_rows),
        "mfn_ckd": len(ckd_codes),
        "mfn_cbu": len(cbu_codes),
        "fta_total": len(fta_rows),
        "acfta": sum(row["regime"] == "ACFTA" for row in fta_rows),
        "rcep": sum(row["regime"] == "RCEP" for row in fta_rows),
    }


def seed_rule_cards(session: Session, clauses: dict[str, str]) -> dict[str, str]:
    rules = [
        (
            "RULE-MY-CBU-TAX-CHAIN-CORRECTED",
            "IMPORT_DUTY",
            "CBU整车法定税链",
            "进口关税按海关价值计算；消费税基础为海关价值加进口关税；"
            "销售税基础为海关价值、进口关税和消费税之和。",
            {"all": [{"field": "vehicle.import_mode", "operator": "EQ", "value": "CBU"}]},
            {
                "import_duty": "customs_value * import_duty_rate",
                "excise": "(customs_value + import_duty) * excise_rate",
                "sales_tax": (
                    "(customs_value + import_duty + excise) * sales_tax_rate"
                ),
            },
            "MY-JKDM",
            "cbu_tax_sequence",
            date(2018, 9, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-CKD-8703-SST-EXEMPT-2025",
            "SALES_TAX",
            "8703整套CKD进口销售税豁免",
            "只有落入P.U. (A) 171/2025所列完整CKD税号的货物，进口销售税率"
            "才按免税处理；不得扩展到未列明的散件。",
            {
                "all": [
                    {
                        "field": "classification.pdk_ckd_line_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                    {
                        "field": "approval.miti_ckd_ap_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            {"import_sales_tax_rate": 0, "scope": "EXACT_167_CKD_LINES"},
            "MY-JKDM",
            "ckd_sst_exempt",
            date(2025, 7, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-CKD-IMPORT-DUTY-NOT-UNIVERSALLY-ZERO",
            "IMPORT_DUTY",
            "CKD进口关税必须按完整税号和原产地制度查询",
            "PDK 2025的CKD税号存在0%、5%、10%及35%等进口关税率；"
            "系统必须读取确切税号及可用的MFN、ACFTA或RCEP税率。",
            {
                "all": [
                    {
                        "field": "vehicle.ckd_tariff_code",
                        "operator": "IS_NOT_NULL",
                    }
                ]
            },
            {"rate_source": "customs.vehicle_tariff_rate_line"},
            "MY-JKDM",
            "ckd_sst_exempt",
            date(2025, 11, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-LOCAL-VEHICLE-EXCISE-2026",
            "EXCISE",
            "本地组装成车消费税",
            "本地制造车辆由持牌制造商在移出制造场所以登记时缴纳消费税，"
            "使用法定税率或经批准的项目税率。",
            {
                "all": [
                    {
                        "field": "approval.local_assembly_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                    {
                        "field": "local.excise_value",
                        "operator": "IS_NOT_NULL",
                    },
                ]
            },
            {"excise": "approved_local_excise_value * selected_excise_rate"},
            "MY-JKDM",
            "local_excise_payment",
            date(2026, 2, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-LOCAL-EXCISE-VALUE-2020",
            "VALUATION",
            "本地制造车辆消费税计税价值",
            "计税价值按公开市场价格确定，并依次使用计算价值或弹性价值；"
            "计算价值包含材料、制造、利润和一般费用。",
            {
                "all": [
                    {"field": "local.excise_value", "operator": "IS_NOT_NULL"},
                    {
                        "field": "local.valuation_method",
                        "operator": "IN",
                        "value": ["OPEN_MARKET", "COMPUTED", "FLEXIBLE"],
                    },
                ]
            },
            {"value_source": "ENTERPRISE_VALUATION_WITH_CUSTOMS_SUPPORT"},
            "MY-JKDM",
            "local_excise_value",
            date(2020, 1, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-LOCAL-VEHICLE-SST-VALUE",
            "VALUATION",
            "本地组装成车销售税计税价值",
            "非关联方销售可用交易价值；关联方、无销售或合同组装情形需按"
            "法定顺序使用计算价值等方法。不得把组装人工费发票直接当成整车税基。",
            {
                "all": [
                    {
                        "field": "local.sales_tax_value",
                        "operator": "IS_NOT_NULL",
                    }
                ]
            },
            {"sales_tax": "determined_local_sales_value * selected_sales_tax_rate"},
            "MY-JKDM",
            "local_sst_value",
            date(2018, 9, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-LOCAL-BEV-EXEMPTION-2027-APPROVAL-GATED",
            "INCENTIVE",
            "本地组装BEV优惠至2027年底且须有项目确认",
            "符合条件并取得项目及税收豁免确认的本地组装BEV，可在2027年"
            "12月31日前适用零部件进口关税、成车消费税及销售税优惠；"
            "没有批文时回退法定税率。",
            {
                "all": [
                    {"field": "vehicle.powertrain", "operator": "EQ", "value": "BEV"},
                    {
                        "field": "approval.local_bev_exemption_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            {
                "component_import_duty_rate": 0,
                "finished_vehicle_excise_rate": 0,
                "finished_vehicle_sales_tax_rate": 0,
                "fallback": "STATUTORY_RATES",
            },
            "MY-MOF",
            "local_bev_2027",
            date(2023, 1, 1),
            date(2028, 1, 1),
            "VERIFIED",
        ),
        (
            "RULE-MY-CBU-BEV-NO-TAX-EXEMPTION-2026",
            "INCENTIVE",
            "2026年CBU纯电动车不得沿用已到期税收豁免",
            "CBU EV特别豁免已于2025年12月31日结束；2026年场景必须使用"
            "现行税号、进口关税、消费税和销售税。",
            {
                "all": [
                    {"field": "vehicle.powertrain", "operator": "EQ", "value": "BEV"},
                    {"field": "vehicle.import_mode", "operator": "EQ", "value": "CBU"},
                    {
                        "field": "scenario.calculation_date",
                        "operator": "GTE",
                        "value": "2026-01-01",
                    },
                ]
            },
            {"expired_benefit": "CBU_BEV_FULL_EXEMPTION", "fallback": "STATUTORY"},
            "MY-MITI",
            "cbu_ev_current",
            date(2026, 1, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-CBU-BEV-IMPORT-CONDITIONS-2026-07",
            "APPROVAL",
            "2026年7月起CBU纯电动车进口门槛",
            "自2026年7月1日起，CBU EV最低CIF为RM200,000且电机功率"
            "至少180kW，并仍须取得适用AP。",
            {
                "all": [
                    {"field": "vehicle.powertrain", "operator": "EQ", "value": "BEV"},
                    {"field": "vehicle.import_mode", "operator": "EQ", "value": "CBU"},
                    {
                        "field": "vehicle.customs_value_myr",
                        "operator": "GTE",
                        "value": 200000,
                    },
                    {
                        "field": "vehicle.motor_power_kw",
                        "operator": "GTE",
                        "value": 180,
                    },
                ]
            },
            None,
            "MY-MITI",
            "cbu_ev_current",
            date(2026, 7, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-ACFTA-8703-RVC40",
            "FTA",
            "ACFTA整车及整套CKD原产地门槛",
            "中国原产8703整车或整套CKD主张ACFTA税率时，需满足RVC40、"
            "直接运输或可接受的中转证据并提供Form E；否则回退MFN。",
            {
                "all": [
                    {
                        "field": "origin.country_iso2",
                        "operator": "EQ",
                        "value": "CN",
                    },
                    {"field": "origin.rvc", "operator": "GTE", "value": 0.40},
                    {
                        "field": "origin.form_e_valid",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            {"rate_source": "ACFTA_CURRENT_2026", "fallback": "MFN"},
            "MY-JKDM",
            "acfta_roo_8703",
            date(2025, 1, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-RCEP-8703-RVC40",
            "FTA",
            "RCEP整车及整套CKD原产地门槛",
            "8703整车或整套CKD主张RCEP税率时，需满足RVC40并提供"
            "Form RCEP或经核准出口商的原产地声明；否则回退MFN。",
            {
                "all": [
                    {
                        "field": "origin.country_iso2",
                        "operator": "EQ",
                        "value": "CN",
                    },
                    {"field": "origin.rvc", "operator": "GTE", "value": 0.40},
                    {
                        "field": "origin.rcep_proof_valid",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            {"rate_source": "RCEP_CURRENT_2026", "fallback": "MFN"},
            "MY-JKDM",
            "rcep_roo_8703",
            date(2026, 3, 31),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-COMPONENT-EXEMPTION-APPROVAL-ONLY",
            "INCENTIVE",
            "原材料及零部件进口关税减免不得默认",
            "制造商可在进口前申请直接用于成品制造的原材料及零部件免税；"
            "只有批文覆盖的税号、数量或价值及有效期可使用批准税率。",
            {
                "all": [
                    {
                        "field": "approval.component_exemption_reference",
                        "operator": "IS_NOT_NULL",
                    },
                    {
                        "field": "approval.component_line_covered",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            {"approved_rate_source": "ENTERPRISE_APPROVAL", "fallback": "STATUTORY"},
            "MY-MIDA",
            "component_exemption",
            date(2020, 7, 29),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-CUSTOMISED-INCENTIVE-NO-PUBLIC-DEFAULT",
            "LOCALIZATION",
            "本地化率与定制化优惠不得设公共默认值",
            "公开政策说明消费税减免采用项目定制机制，但未给出所有企业通用的"
            "本地化率阈值或减免率。必须读取企业项目批准函。",
            {
                "all": [
                    {
                        "field": "approval.customised_incentive_letter",
                        "operator": "IS_NOT_NULL",
                    }
                ]
            },
            {
                "localization_threshold_source": "ENTERPRISE_APPROVAL",
                "excise_reduction_source": "ENTERPRISE_APPROVAL",
                "missing_approval": "STATUTORY_RATE",
            },
            "MY-MIDA",
            "customised_incentive",
            date(2026, 1, 1),
            None,
            "VERIFIED",
        ),
        (
            "RULE-MY-NO-SEPARATE-VAT-GST",
            "VAT_GST",
            "车辆货物税链不另加VAT或GST",
            "马来西亚现行车辆货物链使用单阶段Sales Tax；计算结果不得再叠加"
            "一个独立VAT或GST。服务税只在另有应税服务时进入成本模型。",
            {
                "all": [
                    {
                        "field": "scenario.country_iso2",
                        "operator": "EQ",
                        "value": "MY",
                    }
                ]
            },
            {"vat_rate": 0, "gst_rate": 0, "sales_tax": "SEPARATE_RULE"},
            "MY-JKDM",
            "no_vat",
            date(2018, 9, 1),
            None,
            "VERIFIED",
        ),
    ]
    sql = text(
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
          :content, CAST(:condition AS jsonb),
          CASE WHEN CAST(:formula AS text) IS NULL THEN NULL
               ELSE CAST(:formula AS jsonb) END,
          'PDK 2025 / CURRENT 2026', authority.authority_id,
          :effective_from, :effective_to, 1, CAST(:source_clause_id AS uuid),
          'ACTIVE', CAST(:status AS ref.verification_status),
          CASE WHEN :status = 'VERIFIED' THEN now() ELSE NULL END,
          CASE WHEN :status = 'VERIFIED'
               THEN 'CODEX_OFFICIAL_SOURCE_REVIEW' ELSE NULL END
        FROM ref.country country
        JOIN ref.authority authority
          ON authority.authority_code = :authority_code
        WHERE country.iso2 = 'MY'
        ON CONFLICT (rule_code, version) DO UPDATE SET
          rule_domain = EXCLUDED.rule_domain,
          rule_name_cn = EXCLUDED.rule_name_cn,
          rule_content = EXCLUDED.rule_content,
          condition_expression = EXCLUDED.condition_expression,
          formula_expression = EXCLUDED.formula_expression,
          authority_id = EXCLUDED.authority_id,
          effective_from = EXCLUDED.effective_from,
          effective_to = EXCLUDED.effective_to,
          source_clause_id = EXCLUDED.source_clause_id,
          record_status = 'ACTIVE',
          verification_status = EXCLUDED.verification_status,
          verified_at = EXCLUDED.verified_at,
          verified_by = EXCLUDED.verified_by,
          updated_at = now()
        RETURNING rule_card_id
        """
    )
    rule_ids: dict[str, str] = {}
    for (
        code,
        domain,
        name,
        content,
        condition,
        formula,
        authority,
        clause_key,
        effective_from,
        effective_to,
        status,
    ) in rules:
        rule_ids[code] = str(
            session.execute(
                sql,
                {
                    "code": code,
                    "domain": domain,
                    "name": name,
                    "content": content,
                    "condition": json_text(condition),
                    "formula": json_text(formula) if formula is not None else None,
                    "authority_code": authority,
                    "source_clause_id": clauses[clause_key],
                    "effective_from": effective_from,
                    "effective_to": effective_to,
                    "status": status,
                },
            ).scalar_one()
        )
    return rule_ids


def seed_approvals(session: Session, clauses: dict[str, str]) -> dict[str, str]:
    approvals = [
        (
            "REQ-MY-CBU-N180-OR-FRANCHISE-AP",
            "MANDATORY",
            "CBU_PASSENGER_VEHICLE",
            "CBU",
            None,
            {"all": [{"field": "approval.import_ap", "operator": "IS_NOT_NULL"}]},
            [
                "Applicable MITI AP",
                "Model approval",
                "Invoice",
                "Bill of Lading and packing list",
                "Certificate of Origin or registration as applicable",
            ],
            "MY-MITI",
            "n180_ap",
            date(2026, 1, 1),
            "CBU import is blocked.",
            "VERIFIED",
        ),
        (
            "REQ-MY-CBU-ANNUAL-AP-ALLOCATION",
            "MANDATORY",
            "CBU_AP_QUANTITY",
            "CBU",
            None,
            {
                "all": [
                    {
                        "field": "approval.annual_ap_allocation",
                        "operator": "IS_NOT_NULL",
                    },
                    {
                        "field": "approval.remaining_ap_quantity",
                        "operator": "GT",
                        "value": 0,
                    },
                ]
            },
            [
                "Annual AP allocation letter",
                "Approved model and quantity",
                "Permit validity dates",
            ],
            "MY-MITI",
            "franchise_allocation",
            date(2026, 1, 1),
            "No public quota is assumed; import is blocked above the enterprise allocation.",
            "VERIFIED",
        ),
        (
            "REQ-MY-CBU-BEV-CURRENT-THRESHOLDS",
            "MANDATORY",
            "CBU_BEV_FROM_2026_07_01",
            "CBU",
            "BEV",
            {
                "all": [
                    {
                        "field": "vehicle.customs_value_myr",
                        "operator": "GTE",
                        "value": 200000,
                    },
                    {
                        "field": "vehicle.motor_power_kw",
                        "operator": "GTE",
                        "value": 180,
                    },
                ]
            },
            ["CIF valuation evidence", "Motor power technical specification"],
            "MY-MITI",
            "cbu_ev_current",
            date(2026, 7, 1),
            "CBU EV import eligibility fails.",
            "VERIFIED",
        ),
        (
            "REQ-MY-CKD-AP-AND-DEFINITION",
            "MANDATORY",
            "WHOLE_CKD_KIT",
            "CKD",
            None,
            {
                "all": [
                    {
                        "field": "approval.miti_ckd_ap_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                    {
                        "field": "classification.ckd_definition_confirmed",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            [
                "MITI local-assembly model approval",
                "MITI AP CKD",
                "Packing list and CKD presentation evidence",
                "Customs classification support",
            ],
            "MY-MITI",
            "ckd_route",
            date(2023, 1, 1),
            "Fallback to N205 Parts/Sub-Assemblies; CKD line cannot be assumed.",
            "VERIFIED",
        ),
        (
            "REQ-MY-N205-PARTS-SUBASSEMBLIES",
            "MANDATORY",
            "VEHICLE_PARTS_AND_SUBASSEMBLIES",
            "PARTS",
            None,
            {
                "all": [
                    {"field": "approval.n205", "operator": "IS_NOT_NULL"},
                    {
                        "field": "approval.local_assembly_model",
                        "operator": "IS_NOT_NULL",
                    },
                ]
            },
            [
                "N205 ePermit",
                "MITI local-assembly model approval",
                "Manufacturing licence or contract assembler",
                "Knocked-down or franchise agreement",
                "Vehicle specifications",
                "Bill of Lading and packing list",
                "Invoice",
            ],
            "MY-MITI",
            "n205_ap",
            date(2023, 1, 1),
            "Parts/Sub-Assemblies vehicle project import is blocked.",
            "VERIFIED",
        ),
        (
            "REQ-MY-PART-LEVEL-IMPORT-CONTROL-SCREEN",
            "MANDATORY",
            "EACH_IMPORTED_CCU_OR_EXACT_TARIFF_LINE",
            "PARTS",
            None,
            {
                "all": [
                    {
                        "field": "customs.import_control_screen_complete",
                        "operator": "EQ",
                        "value": True,
                    }
                ]
            },
            [
                "JKDM HS Explorer prohibition schedule result",
                "Applicable line-specific licence or approval",
            ],
            "MY-JKDM",
            "import_control",
            date(2023, 4, 15),
            "Affected line is blocked; unaffected lines may continue separately.",
            "VERIFIED",
        ),
        (
            "REQ-MY-FTA-SHIPMENT-ORIGIN-PROOF",
            "INCENTIVE_ONLY",
            "ACFTA_OR_RCEP_PREFERENCE",
            None,
            None,
            {
                "all": [
                    {
                        "field": "origin.rvc",
                        "operator": "GTE",
                        "value": 0.40,
                    },
                    {
                        "field": "origin.proof_valid",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            [
                "Form E for ACFTA; or Form RCEP / approved-exporter declaration",
                "RVC working papers",
                "Supplier origin evidence",
                "Direct consignment or transit evidence",
            ],
            "MY-JKDM",
            "acfta_roo_8703",
            date(2025, 1, 1),
            "Preferential rate is denied and calculation falls back to MFN.",
            "VERIFIED",
        ),
        (
            "REQ-MY-LOCAL-BEV-EXEMPTION-CONFIRMATION",
            "INCENTIVE_ONLY",
            "LOCALLY_ASSEMBLED_BEV",
            "LOCAL_PRODUCTION",
            "BEV",
            {
                "all": [
                    {
                        "field": "approval.local_bev_exemption_confirmed",
                        "operator": "EQ",
                        "value": True,
                    }
                ]
            },
            [
                "Local assembly project approval",
                "Tax exemption confirmation",
                "Approved component and vehicle schedule",
                "Validity dates",
            ],
            "MY-MOF",
            "local_bev_2027",
            date(2023, 1, 1),
            "Statutory rates apply; zero rates cannot be assumed.",
            "VERIFIED",
        ),
        (
            "REQ-MY-CUSTOMISED-AUTOMOTIVE-INCENTIVE-LETTER",
            "INCENTIVE_ONLY",
            "ICE_HEV_PHEV_EREV_OR_POST_EXEMPTION_BEV_PROJECT",
            "LOCAL_PRODUCTION",
            None,
            {
                "all": [
                    {
                        "field": "approval.customised_incentive_letter",
                        "operator": "IS_NOT_NULL",
                    }
                ]
            },
            [
                "MITI/MIDA project approval or incentive letter",
                "Approved excise reduction schedule",
                "Approved localization, vendor and value-added conditions",
                "Validity and performance conditions",
            ],
            "MY-MIDA",
            "customised_incentive",
            date(2026, 1, 1),
            "Statutory excise and sales-tax rates apply.",
            "VERIFIED",
        ),
        (
            "REQ-MY-COMPONENT-DUTY-EXEMPTION-APPROVAL",
            "INCENTIVE_ONLY",
            "DIRECTLY_IMPORTED_MANUFACTURING_COMPONENTS",
            "PARTS",
            None,
            {
                "all": [
                    {
                        "field": "approval.component_exemption_reference",
                        "operator": "IS_NOT_NULL",
                    },
                    {
                        "field": "approval.line_and_quantity_covered",
                        "operator": "EQ",
                        "value": True,
                    },
                ]
            },
            [
                "MIDA exemption approval",
                "Manufacturing licence or exemption confirmation",
                "Approved tariff lines and quantities or values",
                "Manufacturing process and direct-use evidence",
            ],
            "MY-MIDA",
            "component_exemption",
            date(2020, 7, 29),
            "Statutory duty and sales-tax treatment applies.",
            "VERIFIED",
        ),
    ]
    sql = text(
        """
        INSERT INTO rules.approval_matrix (
          requirement_code, country_id, requirement_type, applicable_object,
          import_mode, powertrain, trigger_condition, required_document,
          authority_id, failure_consequence, effective_from, version,
          source_clause_id, record_status, verification_status
        )
        SELECT
          :code, country.country_id, CAST(:type AS ref.requirement_type), :object,
          CASE WHEN CAST(:mode AS text) IS NULL THEN NULL
               ELSE CAST(:mode AS ref.import_mode) END,
          CASE WHEN CAST(:powertrain AS text) IS NULL THEN NULL
               ELSE CAST(:powertrain AS ref.powertrain) END,
          CAST(:trigger AS jsonb), CAST(:documents AS jsonb),
          authority.authority_id, :failure, :effective_from, 1,
          CAST(:source_clause_id AS uuid), 'ACTIVE',
          CAST(:status AS ref.verification_status)
        FROM ref.country country
        JOIN ref.authority authority
          ON authority.authority_code = :authority_code
        WHERE country.iso2 = 'MY'
        ON CONFLICT (requirement_code, version) DO UPDATE SET
          requirement_type = EXCLUDED.requirement_type,
          applicable_object = EXCLUDED.applicable_object,
          import_mode = EXCLUDED.import_mode,
          powertrain = EXCLUDED.powertrain,
          trigger_condition = EXCLUDED.trigger_condition,
          required_document = EXCLUDED.required_document,
          authority_id = EXCLUDED.authority_id,
          failure_consequence = EXCLUDED.failure_consequence,
          effective_from = EXCLUDED.effective_from,
          source_clause_id = EXCLUDED.source_clause_id,
          record_status = 'ACTIVE',
          verification_status = EXCLUDED.verification_status,
          updated_at = now()
        RETURNING requirement_id
        """
    )
    ids: dict[str, str] = {}
    for (
        code,
        requirement_type,
        applicable_object,
        mode,
        powertrain,
        trigger,
        documents,
        authority,
        clause_key,
        effective_from,
        failure,
        status,
    ) in approvals:
        ids[code] = str(
            session.execute(
                sql,
                {
                    "code": code,
                    "type": requirement_type,
                    "object": applicable_object,
                    "mode": mode,
                    "powertrain": powertrain,
                    "trigger": json_text(trigger),
                    "documents": json_text(documents),
                    "authority_code": authority,
                    "source_clause_id": clauses[clause_key],
                    "effective_from": effective_from,
                    "failure": failure,
                    "status": status,
                },
            ).scalar_one()
        )
    return ids


def seed_scenarios(
    session: Session,
    route_ids: dict[str, str],
    rule_ids: dict[str, str],
    requirement_ids: dict[str, str],
) -> None:
    del route_ids
    scenarios = [
        (
            "SCN-MY-ROUTE-01-CBU",
            "马来西亚路径01：CBU整车进口",
            "CBU",
            ROUTE_CBU,
            cbu_dsl("SCN-MY-ROUTE-01-CBU"),
            "VERIFIED",
        ),
        (
            "SCN-MY-ROUTE-02-CKD-WHOLE-KIT",
            "马来西亚路径02：整套CKD进口及本地组装",
            "CKD",
            ROUTE_CKD,
            ckd_whole_kit_dsl("SCN-MY-ROUTE-02-CKD-WHOLE-KIT"),
            "VERIFIED",
        ),
        (
            "SCN-MY-ROUTE-03-PARTS-SUBASSEMBLIES",
            "马来西亚路径03：分总成税务桶进口及本地组装",
            "PARTS",
            ROUTE_SUBASSEMBLIES,
            bucket_route_dsl(
                "SCN-MY-ROUTE-03-PARTS-SUBASSEMBLIES",
                "SCN-MY-ROUTE-04-PART-LEVEL",
            ),
            "VERIFIED",
        ),
        (
            "SCN-MY-ROUTE-04-PART-LEVEL",
            "马来西亚路径04：CCU零件级进口及本地组装",
            "PARTS",
            ROUTE_PART_LEVEL,
            bucket_route_dsl("SCN-MY-ROUTE-04-PART-LEVEL", None),
            "CANDIDATE",
        ),
        (
            "SCN-MY-ROUTE-05-MIXED-KD",
            "马来西亚路径05：混合KD进口及本地组装",
            "PARTS",
            ROUTE_MIXED,
            bucket_route_dsl("SCN-MY-ROUTE-05-MIXED-KD", None),
            "CANDIDATE",
        ),
    ]
    scenario_sql = text(
        """
        INSERT INTO rules.tax_scenario_model (
          scenario_code, country_id, scenario_name_cn, import_mode,
          origin_regime, classification_route, required_input_fields,
          calculation_dsl, output_scope, effective_from, version,
          record_status, verification_status
        )
        SELECT
          :code, country.country_id, :name, CAST(:mode AS ref.import_mode),
          'UNKNOWN', :route, CAST(:required AS jsonb), CAST(:dsl AS jsonb),
          CAST(:output_scope AS jsonb), DATE '2025-11-01', 1, 'ACTIVE',
          CAST(:status AS ref.verification_status)
        FROM ref.country country
        WHERE country.iso2 = 'MY'
        ON CONFLICT (scenario_code, version) DO UPDATE SET
          scenario_name_cn = EXCLUDED.scenario_name_cn,
          import_mode = EXCLUDED.import_mode,
          origin_regime = EXCLUDED.origin_regime,
          classification_route = EXCLUDED.classification_route,
          required_input_fields = EXCLUDED.required_input_fields,
          calculation_dsl = EXCLUDED.calculation_dsl,
          output_scope = EXCLUDED.output_scope,
          record_status = 'ACTIVE',
          verification_status = EXCLUDED.verification_status,
          updated_at = now()
        RETURNING scenario_model_id
        """
    )
    scenario_ids: dict[str, str] = {}
    for code, name, mode, route, dsl, status in scenarios:
        required = [
            item["path"] for item in dsl["inputs"] if item.get("required", False)
        ]
        scenario_ids[code] = str(
            session.execute(
                scenario_sql,
                {
                    "code": code,
                    "name": name,
                    "mode": mode,
                    "route": route,
                    "required": json_text(required),
                    "dsl": json_text(dsl),
                    "output_scope": json_text(
                        {
                            "tax_layers": ["IMPORT", "LOCAL_FINISHED_VEHICLE"],
                            "metrics": [
                                "TOTAL_TAX",
                                "EFFECTIVE_TAX_RATE",
                                "TAX_AFTER_APPROVED_INCENTIVES",
                                "CBU_VS_KD_PROFIT_COMPARISON",
                            ],
                            "audit_trace_required": True,
                        }
                    ),
                    "status": status,
                },
            ).scalar_one()
        )

    rule_links = {
        "SCN-MY-ROUTE-01-CBU": [
            "RULE-MY-CBU-TAX-CHAIN-CORRECTED",
            "RULE-MY-CBU-BEV-NO-TAX-EXEMPTION-2026",
            "RULE-MY-CBU-BEV-IMPORT-CONDITIONS-2026-07",
            "RULE-MY-ACFTA-8703-RVC40",
            "RULE-MY-RCEP-8703-RVC40",
            "RULE-MY-NO-SEPARATE-VAT-GST",
        ],
        "SCN-MY-ROUTE-02-CKD-WHOLE-KIT": [
            "RULE-MY-CKD-8703-SST-EXEMPT-2025",
            "RULE-MY-CKD-IMPORT-DUTY-NOT-UNIVERSALLY-ZERO",
            "RULE-MY-LOCAL-VEHICLE-EXCISE-2026",
            "RULE-MY-LOCAL-EXCISE-VALUE-2020",
            "RULE-MY-LOCAL-VEHICLE-SST-VALUE",
            "RULE-MY-LOCAL-BEV-EXEMPTION-2027-APPROVAL-GATED",
            "RULE-MY-CUSTOMISED-INCENTIVE-NO-PUBLIC-DEFAULT",
            "RULE-MY-NO-SEPARATE-VAT-GST",
        ],
        "SCN-MY-ROUTE-03-PARTS-SUBASSEMBLIES": [
            "RULE-MY-COMPONENT-EXEMPTION-APPROVAL-ONLY",
            "RULE-MY-LOCAL-VEHICLE-EXCISE-2026",
            "RULE-MY-LOCAL-EXCISE-VALUE-2020",
            "RULE-MY-LOCAL-VEHICLE-SST-VALUE",
            "RULE-MY-LOCAL-BEV-EXEMPTION-2027-APPROVAL-GATED",
            "RULE-MY-CUSTOMISED-INCENTIVE-NO-PUBLIC-DEFAULT",
            "RULE-MY-NO-SEPARATE-VAT-GST",
        ],
        "SCN-MY-ROUTE-04-PART-LEVEL": [
            "RULE-MY-COMPONENT-EXEMPTION-APPROVAL-ONLY",
            "RULE-MY-LOCAL-VEHICLE-EXCISE-2026",
            "RULE-MY-LOCAL-EXCISE-VALUE-2020",
            "RULE-MY-LOCAL-VEHICLE-SST-VALUE",
            "RULE-MY-CUSTOMISED-INCENTIVE-NO-PUBLIC-DEFAULT",
            "RULE-MY-NO-SEPARATE-VAT-GST",
        ],
        "SCN-MY-ROUTE-05-MIXED-KD": [
            "RULE-MY-CKD-8703-SST-EXEMPT-2025",
            "RULE-MY-COMPONENT-EXEMPTION-APPROVAL-ONLY",
            "RULE-MY-LOCAL-VEHICLE-EXCISE-2026",
            "RULE-MY-LOCAL-EXCISE-VALUE-2020",
            "RULE-MY-LOCAL-VEHICLE-SST-VALUE",
            "RULE-MY-CUSTOMISED-INCENTIVE-NO-PUBLIC-DEFAULT",
            "RULE-MY-NO-SEPARATE-VAT-GST",
        ],
    }
    rule_link_sql = text(
        """
        INSERT INTO rules.scenario_rule_link (
          scenario_model_id, rule_card_id, sequence_no, mandatory
        ) VALUES (
          CAST(:scenario_id AS uuid), CAST(:rule_id AS uuid), :sequence_no, true
        )
        ON CONFLICT (scenario_model_id, rule_card_id) DO UPDATE SET
          sequence_no = EXCLUDED.sequence_no,
          mandatory = true
        """
    )
    for scenario_code, codes in rule_links.items():
        for sequence_no, code in enumerate(codes, start=1):
            session.execute(
                rule_link_sql,
                {
                    "scenario_id": scenario_ids[scenario_code],
                    "rule_id": rule_ids[code],
                    "sequence_no": sequence_no,
                },
            )

    requirement_links = {
        "SCN-MY-ROUTE-01-CBU": [
            "REQ-MY-CBU-N180-OR-FRANCHISE-AP",
            "REQ-MY-CBU-ANNUAL-AP-ALLOCATION",
            "REQ-MY-CBU-BEV-CURRENT-THRESHOLDS",
            "REQ-MY-FTA-SHIPMENT-ORIGIN-PROOF",
        ],
        "SCN-MY-ROUTE-02-CKD-WHOLE-KIT": [
            "REQ-MY-CKD-AP-AND-DEFINITION",
            "REQ-MY-FTA-SHIPMENT-ORIGIN-PROOF",
            "REQ-MY-LOCAL-BEV-EXEMPTION-CONFIRMATION",
            "REQ-MY-CUSTOMISED-AUTOMOTIVE-INCENTIVE-LETTER",
        ],
        "SCN-MY-ROUTE-03-PARTS-SUBASSEMBLIES": [
            "REQ-MY-N205-PARTS-SUBASSEMBLIES",
            "REQ-MY-PART-LEVEL-IMPORT-CONTROL-SCREEN",
            "REQ-MY-FTA-SHIPMENT-ORIGIN-PROOF",
            "REQ-MY-LOCAL-BEV-EXEMPTION-CONFIRMATION",
            "REQ-MY-CUSTOMISED-AUTOMOTIVE-INCENTIVE-LETTER",
            "REQ-MY-COMPONENT-DUTY-EXEMPTION-APPROVAL",
        ],
        "SCN-MY-ROUTE-04-PART-LEVEL": [
            "REQ-MY-PART-LEVEL-IMPORT-CONTROL-SCREEN",
            "REQ-MY-FTA-SHIPMENT-ORIGIN-PROOF",
            "REQ-MY-LOCAL-BEV-EXEMPTION-CONFIRMATION",
            "REQ-MY-CUSTOMISED-AUTOMOTIVE-INCENTIVE-LETTER",
            "REQ-MY-COMPONENT-DUTY-EXEMPTION-APPROVAL",
        ],
        "SCN-MY-ROUTE-05-MIXED-KD": [
            "REQ-MY-CKD-AP-AND-DEFINITION",
            "REQ-MY-N205-PARTS-SUBASSEMBLIES",
            "REQ-MY-PART-LEVEL-IMPORT-CONTROL-SCREEN",
            "REQ-MY-FTA-SHIPMENT-ORIGIN-PROOF",
            "REQ-MY-LOCAL-BEV-EXEMPTION-CONFIRMATION",
            "REQ-MY-CUSTOMISED-AUTOMOTIVE-INCENTIVE-LETTER",
            "REQ-MY-COMPONENT-DUTY-EXEMPTION-APPROVAL",
        ],
    }
    requirement_link_sql = text(
        """
        INSERT INTO rules.scenario_requirement_link (
          scenario_model_id, requirement_id, sequence_no, blocking
        ) VALUES (
          CAST(:scenario_id AS uuid), CAST(:requirement_id AS uuid),
          :sequence_no, :blocking
        )
        ON CONFLICT (scenario_model_id, requirement_id) DO UPDATE SET
          sequence_no = EXCLUDED.sequence_no,
          blocking = EXCLUDED.blocking
        """
    )
    for scenario_code, codes in requirement_links.items():
        for sequence_no, code in enumerate(codes, start=1):
            session.execute(
                requirement_link_sql,
                {
                    "scenario_id": scenario_ids[scenario_code],
                    "requirement_id": requirement_ids[code],
                    "sequence_no": sequence_no,
                    "blocking": code
                    not in {
                        "REQ-MY-FTA-SHIPMENT-ORIGIN-PROOF",
                        "REQ-MY-LOCAL-BEV-EXEMPTION-CONFIRMATION",
                        "REQ-MY-CUSTOMISED-AUTOMOTIVE-INCENTIVE-LETTER",
                        "REQ-MY-COMPONENT-DUTY-EXEMPTION-APPROVAL",
                    },
                },
            )


def correct_existing_scenarios(session: Session) -> None:
    session.execute(
        text(
            """
            UPDATE rules.country_rule_card
            SET
              rule_content =
                'Imported CBU tax sequence: import duty on customs value; excise '
                'on customs value plus import duty; sales tax on customs value plus '
                'import duty plus excise.',
              formula_expression = CAST(:formula AS jsonb),
              updated_at = now()
            WHERE rule_code = 'RULE-MY-CBU-VEHICLE-TAX-SEQUENCE-2025'
              AND version = 1
            """
        ),
        {
            "formula": json_text(
                {
                    "sequence": ["IMPORT_DUTY", "EXCISE", "SST"],
                    "import_duty": "customs_value * import_duty_rate",
                    "excise": "(customs_value + import_duty) * excise_rate",
                    "sales_tax": (
                        "(customs_value + import_duty + excise) * sales_tax_rate"
                    ),
                }
            )
        },
    )
    rows = session.execute(
        text(
            """
            SELECT scenario_model_id, scenario_code
            FROM rules.tax_scenario_model
            WHERE scenario_code LIKE 'SCN-MY-CBU-%-2025'
               OR scenario_code LIKE 'SCN-MY-LOCAL-%'
            """
        )
    ).mappings()
    for row in rows:
        code = row["scenario_code"]
        dsl = cbu_dsl(code) if code.startswith("SCN-MY-CBU-") else local_only_dsl(code)
        required = [
            item["path"] for item in dsl["inputs"] if item.get("required", False)
        ]
        session.execute(
            text(
                """
                UPDATE rules.tax_scenario_model
                SET required_input_fields = CAST(:required AS jsonb),
                    calculation_dsl = CAST(:dsl AS jsonb),
                    updated_at = now()
                WHERE scenario_model_id = CAST(:scenario_id AS uuid)
                """
            ),
            {
                "required": json_text(required),
                "dsl": json_text(dsl),
                "scenario_id": str(row["scenario_model_id"]),
            },
        )


def main() -> None:
    engine = create_engine(database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        ensure_reference_data(session)
        clauses = seed_policy_sources(session)
        route_ids = seed_routes(session, clauses)
        seed_buckets(session, clauses)
        tariff_counts = seed_vehicle_tariff_rates(session, route_ids, clauses)
        rule_ids = seed_rule_cards(session, clauses)
        requirement_ids = seed_approvals(session, clauses)
        seed_scenarios(session, route_ids, rule_ids, requirement_ids)
        correct_existing_scenarios(session)
        session.commit()

    print("Malaysia five-route model seed completed")
    print(f"MFN PDK vehicle lines: {tariff_counts['mfn_total']}")
    print(f"  CBU: {tariff_counts['mfn_cbu']}")
    print(f"  CKD: {tariff_counts['mfn_ckd']}")
    print(f"ACFTA exact current-rate lines: {tariff_counts['acfta']}")
    print(f"RCEP exact current-rate lines: {tariff_counts['rcep']}")
    print(
        "Total exact vehicle tariff-rate records: "
        f"{tariff_counts['mfn_total'] + tariff_counts['fta_total']}"
    )
    print(f"Completed at: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
