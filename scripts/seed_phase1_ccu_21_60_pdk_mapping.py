from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = (
    PROJECT_ROOT / "spec" / "phase1_malaysia_ccu_21_60_pdk_selection.yaml"
)
EXTRACT_PATH = (
    PROJECT_ROOT / "outputs" / "malaysia_pdk2025_research_extract.csv"
)
EVIDENCE_DIR = (
    PROJECT_ROOT / "storage" / "evidence" / "my" / "2026-07-29"
)


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_json(value: Any) -> str:
    return f"{sql_literal(json.dumps(value, ensure_ascii=False))}::jsonb"


def parse_percent(value: str, field_name: str, code: str) -> float:
    normalized = value.strip()
    if not normalized.endswith("%"):
        raise ValueError(
            f"{code}: official extract has no usable {field_name}: {value!r}"
        )
    return float(normalized.removesuffix("%")) / 100.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


selection = yaml.safe_load(SELECTION_PATH.read_text(encoding="utf-8"))
with EXTRACT_PATH.open(encoding="utf-8-sig", newline="") as handle:
    extract_rows = {
        row["national_tariff_code"]: row for row in csv.DictReader(handle)
    }

selected_codes: set[str] = set()
for item in selection["selections"]:
    selected_codes.update(str(code) for code in item.get("codes", []))

missing_extract_codes = sorted(selected_codes - extract_rows.keys())
if missing_extract_codes:
    raise ValueError(
        "Selected national codes missing from JKDM extract: "
        + ", ".join(missing_extract_codes)
    )

source_by_hs6: dict[str, dict[str, str]] = {}
selected_rows_by_hs6: dict[str, list[dict[str, str]]] = defaultdict(list)
for code in sorted(selected_codes):
    row = extract_rows[code]
    hs6 = row["hs6_query"]
    source_by_hs6[hs6] = row
    selected_rows_by_hs6[hs6].append(row)

sql: list[str] = ["BEGIN;"]

for hs6, row in sorted(source_by_hs6.items()):
    source_code = f"SRC-MY-JKDM-PDK2025-{hs6}-P1-60-20260729"
    source_file = EVIDENCE_DIR / row["source_file"]
    if not source_file.exists():
        raise FileNotFoundError(source_file)
    actual_hash = sha256(source_file)
    if actual_hash != row["source_sha256"]:
        raise ValueError(f"{hs6}: archived source hash changed")

    sql.append(
        f"""
INSERT INTO evidence.source_document (
  source_code, authority_id, document_title, source_type, official_status,
  canonical_url, effective_from, accessed_at, language_code,
  content_sha256, archived_object_key, version, record_status
) VALUES (
  {sql_literal(source_code)},
  (SELECT authority_id FROM ref.authority WHERE authority_code='MY-JKDM'),
  {sql_literal(f'JKDM HS Explorer PDK 2025 result - HS {hs6}')},
  'OFFICIAL_PORTAL','OFFICIAL',
  'https://ezhs.customs.gov.my/public-find-hs-data',
  DATE '2025-11-01', TIMESTAMPTZ '2026-07-29 15:00:00+08','en',
  {sql_literal(actual_hash)},
  {sql_literal(f'evidence/my/2026-07-29/{row["source_file"]}')},
  1,'ACTIVE'
)
ON CONFLICT (source_code) DO UPDATE SET
  accessed_at=EXCLUDED.accessed_at,
  content_sha256=EXCLUDED.content_sha256,
  archived_object_key=EXCLUDED.archived_object_key,
  record_status='ACTIVE';
"""
    )

    summaries = []
    for selected_row in selected_rows_by_hs6[hs6]:
        summaries.append(
            f'{selected_row["national_tariff_code"]}: '
            f'{selected_row["description"]}; '
            f'import {selected_row["import_rate"]}; '
            f'SST {selected_row["sst"]}.'
        )
    summary = " ".join(summaries)
    clause_code = f"CLAUSE-MY-PDK2025-{hs6}-P1-60"
    locator = (
        f"POST hsType=PDK; hsCriteria=1; hsKeyword={hs6}; find_item=yes"
    )
    sql.append(
        f"""
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary, extraction_method,
  extracted_at, verification_status
) VALUES (
  {sql_literal(clause_code)},
  (SELECT source_document_id FROM evidence.source_document
   WHERE source_code={sql_literal(source_code)}),
  'PORTAL_QUERY', {sql_literal(locator)}, {sql_literal(summary)},
  {sql_literal(summary)}, {sql_literal(summary)},
  'SCRIPT_EXTRACTED_AND_RULE_REVIEWED',
  TIMESTAMPTZ '2026-07-29 15:30:00+08','VERIFIED'
)
ON CONFLICT (clause_code) DO UPDATE SET
  original_text=EXCLUDED.original_text,
  translated_text_cn=EXCLUDED.translated_text_cn,
  evidence_summary=EXCLUDED.evidence_summary,
  extracted_at=EXCLUDED.extracted_at,
  verification_status='VERIFIED';
"""
    )

mapping_count = 0
for item in selection["selections"]:
    ccu_code = item["ccu"]
    status = item["status"]
    needs = item.get("needs", [])
    codes = [str(code) for code in item.get("codes", [])]

    if status == "UNVERIFIED":
        field_path = (
            f"customs.pdk2025.national_line_selection[{ccu_code}]"
        )
        description = (
            "Round-one research did not identify a defensible national "
            "tariff line without additional technical or authority evidence."
        )
        next_action = (
            "Supply or verify: " + ", ".join(needs)
            + "; then perform legal-note and PDK parent-indentation review."
        )
        sql.append(
            f"""
INSERT INTO audit.missing_data (
  calculation_run_id, field_path, description, data_owner,
  data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
)
SELECT NULL, {sql_literal(field_path)}, {sql_literal(description)},
       'CUSTOMS_CLASSIFICATION_OWNER_AND_ENTERPRISE',
       'AUTHORITY_CONFIRMATION','MIXED',
       {sql_literal(f'FINAL_NATIONAL_TARIFF_SELECTION_FOR_{ccu_code}')},
       'P0', {sql_literal(next_action)},
       'https://ezhs.customs.gov.my/','WAITING_AUTHORITY'
WHERE NOT EXISTS (
  SELECT 1 FROM audit.missing_data
  WHERE field_path={sql_literal(field_path)}
);
"""
        )
        continue

    for national_code in codes:
        row = extract_rows[national_code]
        hs6 = row["hs6_query"]
        duty = parse_percent(
            row["import_rate"], "import rate", national_code
        )
        sst = parse_percent(row["sst"], "SST rate", national_code)
        rate_type = "ZERO" if duty == 0 else "AD_VALOREM"
        control_file_name = (
            f"JKDM_HS_Explorer_Import_Control_{national_code}.html"
        )
        control_file = EVIDENCE_DIR / control_file_name
        if not control_file.exists():
            raise FileNotFoundError(control_file)
        control_hash = sha256(control_file)
        control_text = control_file.read_text(
            encoding="utf-8", errors="replace"
        )
        control_observation = (
            "NO_DATA_DISPLAYED"
            if len(control_text.strip()) < 500
            or "no data" in control_text.lower()
            else "CONTROL_DETAIL_DISPLAYED"
        )
        mapping_code = (
            "MAP-MY-PDK2025-MFN-"
            + ccu_code.removeprefix("CCU-")
            + "-"
            + national_code
        )
        eligibility = {
            "required_fields": needs,
            "selection_status": status,
            "final_classification_requires_use_time_gate": True,
        }
        additional = {
            "customs_unit": row["unit"],
            "sst": {
                "displayed_rate": sst,
                "portal_display_verified": True,
                "calculation_rule_code": "RULE-MY-SST-IMPORT-BASE-2018",
            },
            "portal_import_control": {
                "result": control_observation,
                "observed_on": "2026-07-29",
                "legal_conclusion": False,
                "content_sha256": control_hash,
                "archived_object_key": (
                    f"evidence/my/2026-07-29/{control_file_name}"
                ),
            },
            "verification_scope": (
                "PDK national line, MFN rate and displayed SST are sourced; "
                "final enterprise-part classification remains use-time gated."
            ),
        }
        clause_code = f"CLAUSE-MY-PDK2025-{hs6}-P1-60"

        sql.append(
            f"""
INSERT INTO customs.tariff_mapping (
  mapping_code, country_id, candidate_id, tariff_version,
  national_tariff_code, tariff_description, origin_regime,
  trade_agreement_id, duty_rate, rate_type, additional_measure,
  eligibility_condition, effective_from, effective_to, version,
  source_clause_id, record_status, verification_status
)
SELECT
  {sql_literal(mapping_code)},
  (SELECT country_id FROM ref.country WHERE iso2='MY'),
  candidate.candidate_id, 'PDK 2025', {sql_literal(national_code)},
  {sql_literal(row["description"])}, 'MFN', NULL,
  {duty:.8f}, '{rate_type}', {sql_json(additional)},
  {sql_json(eligibility)}, DATE '2025-11-01', NULL, 1,
  (SELECT source_clause_id FROM evidence.source_clause
   WHERE clause_code={sql_literal(clause_code)}),
  'ACTIVE', {sql_literal(status)}
FROM customs.ccu_candidate_hs candidate
JOIN customs.customs_classification_unit ccu
  ON ccu.ccu_id=candidate.ccu_id
WHERE ccu.ccu_code={sql_literal(ccu_code)}
  AND ccu.version=1
  AND candidate.hs6_code={sql_literal(hs6)}
ON CONFLICT (mapping_code,version) DO UPDATE SET
  candidate_id=EXCLUDED.candidate_id,
  national_tariff_code=EXCLUDED.national_tariff_code,
  tariff_description=EXCLUDED.tariff_description,
  duty_rate=EXCLUDED.duty_rate,
  rate_type=EXCLUDED.rate_type,
  additional_measure=EXCLUDED.additional_measure,
  eligibility_condition=EXCLUDED.eligibility_condition,
  source_clause_id=EXCLUDED.source_clause_id,
  record_status='ACTIVE',
  verification_status=EXCLUDED.verification_status,
  updated_at=now();
"""
        )
        mapping_count += 1

    if status == "CANDIDATE":
        field_path = (
            f"enterprise.classification_input[{ccu_code}]."
            "final_national_line_selection"
        )
        description = (
            "PDK 2025 national lines and rates are recorded, but final "
            "selection remains conditional on use-time technical inputs."
        )
        next_action = "Supply and verify: " + ", ".join(needs)
        sql.append(
            f"""
INSERT INTO audit.missing_data (
  calculation_run_id, field_path, description, data_owner,
  data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
)
SELECT NULL, {sql_literal(field_path)}, {sql_literal(description)},
       'ENTERPRISE_TECHNICAL_OWNER',
       'ENTERPRISE_INPUT','ENTERPRISE',
       {sql_literal(f'FINAL_NATIONAL_TARIFF_SELECTION_FOR_{ccu_code}')},
       'P0', {sql_literal(next_action)}, NULL, 'WAITING_ENTERPRISE'
WHERE NOT EXISTS (
  SELECT 1 FROM audit.missing_data
  WHERE field_path={sql_literal(field_path)}
);
"""
        )

sql.extend(
    [
        "COMMIT;",
        (
            "SELECT verification_status, count(*) AS mapping_count "
            "FROM customs.tariff_mapping "
            "WHERE mapping_code LIKE 'MAP-MY-PDK2025-MFN-%' "
            "AND eligibility_condition->>'final_classification_requires_use_time_gate'='true' "
            "GROUP BY verification_status ORDER BY verification_status;"
        ),
    ]
)

completed = subprocess.run(
    [
        "docker",
        "compose",
        "exec",
        "-T",
        "postgres",
        "sh",
        "-c",
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
    ],
    cwd=PROJECT_ROOT,
    input="\n".join(sql),
    text=True,
    encoding="utf-8",
    check=False,
)
if completed.returncode:
    raise SystemExit(completed.returncode)

print(f"Prepared and upserted mappings: {mapping_count}")
print("UNVERIFIED CCUs remain represented only as blocking missing-data records.")
