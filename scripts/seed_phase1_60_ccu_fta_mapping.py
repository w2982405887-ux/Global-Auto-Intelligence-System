from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "outputs" / "malaysia_fta_2026_research_extract.csv"
EVIDENCE = ROOT / "storage" / "evidence" / "my" / "2026-07-29"
REGIMES = ("ACFTA", "RCEP")
CORRELATION_OVERRIDES = {
    # RCEP table uses 85272100xx while PDK/ACFTA use 852721x000.
    # Descriptions provide a one-to-one correlation for these two branches.
    ("RCEP", "8527211000"): "8527210010",
    ("RCEP", "8527219000"): "8527210090",
}


def q(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def qjson(value: Any) -> str:
    return q(json.dumps(value, ensure_ascii=False)) + "::jsonb"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rate(value: str) -> float | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("%"):
        normalized = normalized[:-1]
    if not re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return None
    return float(normalized) / 100.0


def psql_csv(query: str) -> list[dict[str, str]]:
    result = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres", "sh", "-c",
            'psql --csv -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" '
            '-d "$POSTGRES_DB"',
        ],
        cwd=ROOT,
        input=query,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    return list(csv.DictReader(io.StringIO(result.stdout)))


with EXTRACT.open(encoding="utf-8-sig", newline="") as handle:
    extracted = list(csv.DictReader(handle))

fta_by_exact: dict[tuple[str, str], dict[str, str]] = {}
fta_by_hs6: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
for row in extracted:
    parsed_rate = rate(row["current_rate"])
    if parsed_rate is None:
        continue
    key = (row["regime"], row["national_tariff_code"])
    fta_by_exact[key] = row
    fta_by_hs6[(row["regime"], row["hs6_query"])].append(row)

mfn_rows = psql_csv(
    """
SELECT
  c.ccu_code,
  h.candidate_id::text,
  h.hs6_code,
  m.national_tariff_code,
  m.tariff_description,
  m.verification_status::text,
  m.additional_measure::text
FROM customs.customs_classification_unit c
JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
JOIN customs.tariff_mapping m ON m.candidate_id=h.candidate_id
WHERE c.unit_level='CUSTOMS_CLASSIFICATION_UNIT'
  AND c.record_status='ACTIVE'
  AND m.origin_regime='MFN'
  AND m.tariff_version='PDK 2025'
  AND m.record_status='ACTIVE'
ORDER BY c.ccu_code, m.national_tariff_code;
"""
)

existing_coverage = {
    (row["ccu_code"], row["agreement_code"])
    for row in psql_csv(
        """
SELECT DISTINCT c.ccu_code, ta.agreement_code
FROM customs.customs_classification_unit c
JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
JOIN customs.tariff_mapping m ON m.candidate_id=h.candidate_id
JOIN ref.trade_agreement ta
  ON ta.trade_agreement_id=m.trade_agreement_id
WHERE m.origin_regime='FTA' AND m.record_status='ACTIVE';
"""
    )
}

sql = ["BEGIN;"]
source_pairs: set[tuple[str, str]] = set()
created = defaultdict(int)
unresolved = defaultdict(set)
resolved_correlations: set[tuple[str, str]] = set()

for mfn in mfn_rows:
    ccu = mfn["ccu_code"]
    hs6 = mfn["hs6_code"]
    mfn_code = mfn["national_tariff_code"]
    mfn_additional = json.loads(mfn["additional_measure"])

    for regime in REGIMES:
        if (ccu, regime) in existing_coverage:
            continue

        override_code = CORRELATION_OVERRIDES.get((regime, mfn_code))
        exact = (
            fta_by_exact.get((regime, override_code))
            if override_code
            else fta_by_exact.get((regime, mfn_code))
        )
        correlation = "EXACT_NATIONAL_CODE"
        if override_code:
            correlation = "CROSS_VERSION_DESCRIPTION_MATCH"
            resolved_correlations.add((regime, ccu))
        selected = exact
        if selected is None:
            candidates = fta_by_hs6.get((regime, hs6), [])
            if len(candidates) == 1:
                selected = candidates[0]
                correlation = "UNIQUE_HS6_RATE_LINE"
            else:
                unresolved[regime].add(ccu)
                continue

        pair = (regime, hs6)
        source_code = f"SRC-MY-JKDM-{regime}-{hs6}-RATE2026-P1-60"
        clause_code = f"CLAUSE-MY-{regime}-{hs6}-RATE2026-P1-60"
        source_file = EVIDENCE / selected["source_file"]
        if not source_file.exists():
            raise FileNotFoundError(source_file)
        if digest(source_file) != selected["source_sha256"]:
            raise ValueError(f"Evidence hash mismatch: {source_file}")

        if pair not in source_pairs:
            source_pairs.add(pair)
            summary_rows = fta_by_hs6[pair]
            summary = " ".join(
                f'{row["national_tariff_code"]}: {row["description"]}; '
                f'current rate {row["current_rate"]}.'
                for row in summary_rows
            )
            sql.append(
                f"""
INSERT INTO evidence.source_document (
  source_code, authority_id, document_title, source_type, official_status,
  canonical_url, effective_from, accessed_at, language_code,
  content_sha256, archived_object_key, version, record_status
) VALUES (
  {q(source_code)},
  (SELECT authority_id FROM ref.authority WHERE authority_code='MY-JKDM'),
  {q(f'JKDM HS Explorer {regime} current rate 2026 - HS {hs6}')},
  'OFFICIAL_PORTAL','OFFICIAL',
  'https://ezhs.customs.gov.my/public-find-hs-data',
  DATE '2026-01-01', TIMESTAMPTZ '2026-07-29 17:00:00+08','en',
  {q(selected["source_sha256"])},
  {q(f'evidence/my/2026-07-29/{selected["source_file"]}')},
  1,'ACTIVE'
)
ON CONFLICT (source_code) DO UPDATE SET
  accessed_at=EXCLUDED.accessed_at,
  content_sha256=EXCLUDED.content_sha256,
  archived_object_key=EXCLUDED.archived_object_key,
  record_status='ACTIVE';

INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary, extraction_method,
  extracted_at, verification_status
) VALUES (
  {q(clause_code)},
  (SELECT source_document_id FROM evidence.source_document
   WHERE source_code={q(source_code)}),
  'PORTAL_QUERY',
  {q(f'POST hsType={regime}; hsCriteria=1; hsKeyword={hs6}; find_item=yes')},
  {q(summary)}, {q(summary)}, {q(summary)},
  'SCRIPT_EXTRACTED_AND_RULE_REVIEWED',
  TIMESTAMPTZ '2026-07-29 17:10:00+08','VERIFIED'
)
ON CONFLICT (clause_code) DO UPDATE SET
  original_text=EXCLUDED.original_text,
  translated_text_cn=EXCLUDED.translated_text_cn,
  evidence_summary=EXCLUDED.evidence_summary,
  extracted_at=EXCLUDED.extracted_at,
  verification_status='VERIFIED';
"""
            )

        fta_rate = rate(selected["current_rate"])
        assert fta_rate is not None
        verification = (
            "VERIFIED"
            if correlation == "EXACT_NATIONAL_CODE"
            and mfn["verification_status"] == "VERIFIED"
            else "CANDIDATE"
        )
        required = (
            [
                "origin.country",
                "origin.form_e",
                "origin.psr_compliance",
                "origin.direct_consignment",
            ]
            if regime == "ACFTA"
            else [
                "origin.country",
                "origin.rcep_proof",
                "origin.psr_compliance",
                "origin.direct_consignment",
            ]
        )
        eligibility = {
            "origin_country": "CN",
            "agreement": regime,
            "required_fields": required,
            "preferential_rate_requires_verified_origin": True,
            "fallback_regime": "MFN",
        }
        additional = {
            "nomenclature_correlation_status": correlation,
            "mfn_national_tariff_code": mfn_code,
            "mfn_mapping_verification": mfn["verification_status"],
            "sst": mfn_additional.get("sst", {}),
            "origin_eligibility_evaluated": False,
        }
        fta_code = selected["national_tariff_code"]
        mapping_code = (
            f"MAP-MY-{regime}-2026-"
            f"{ccu.removeprefix('CCU-')}-{fta_code}"
        )
        tariff_version = f"{regime}-RATE-2026"
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
  {q(mapping_code)},
  (SELECT country_id FROM ref.country WHERE iso2='MY'),
  {q(mfn["candidate_id"])}::uuid, {q(tariff_version)},
  {q(fta_code)}, {q(selected["description"])}, 'FTA',
  (SELECT trade_agreement_id FROM ref.trade_agreement
   WHERE agreement_code={q(regime)}),
  {fta_rate:.8f},
  {q('ZERO' if fta_rate == 0 else 'AD_VALOREM')}::ref.rate_type,
  {qjson(additional)}, {qjson(eligibility)},
  DATE '2026-01-01', NULL, 1,
  (SELECT source_clause_id FROM evidence.source_clause
   WHERE clause_code={q(clause_code)}),
  'ACTIVE', {q(verification)}
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
        created[regime] += 1

for regime, ccus in unresolved.items():
    for ccu in sorted(ccus):
        field_path = (
            f"customs.tariff_mapping[{regime}]"
            f"[{ccu}].nomenclature_correlation"
        )
        sql.append(
            f"""
INSERT INTO audit.missing_data (
  calculation_run_id, field_path, description, data_owner,
  data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
)
SELECT NULL, {q(field_path)},
  {q('The MFN national line has no exact FTA-code match and the FTA HS6 contains multiple current-rate lines.')},
  'CUSTOMS_CLASSIFICATION_OWNER',
  'PUBLIC_RESEARCH','PUBLIC',
  {q(f'{regime}_NOMENCLATURE_CORRELATION_FOR_{ccu}')},
  'P0',
  {q('Resolve the tariff-version correlation from the official schedule or obtain customs/broker confirmation before applying preference.')},
  'https://ezhs.customs.gov.my/','IN_RESEARCH'
WHERE NOT EXISTS (
  SELECT 1 FROM audit.missing_data WHERE field_path={q(field_path)}
);
"""
        )

for regime, ccu in sorted(resolved_correlations):
    field_path = (
        f"customs.tariff_mapping[{regime}]"
        f"[{ccu}].nomenclature_correlation"
    )
    sql.append(
        f"""
UPDATE audit.missing_data
SET status='RESOLVED', resolved_at=COALESCE(resolved_at,now()),
    description=description ||
      ' Resolved by an explicit cross-version description correlation.'
WHERE field_path={q(field_path)}
  AND status<>'RESOLVED';
"""
    )

sql.append("COMMIT;")
result = subprocess.run(
    [
        "docker", "compose", "exec", "-T", "postgres", "sh", "-c",
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
    ],
    cwd=ROOT,
    input="\n".join(sql),
    text=True,
    encoding="utf-8",
    check=False,
)
if result.returncode:
    raise SystemExit(result.returncode)

print("Created or updated:", dict(created))
print("Unresolved CCU correlations:", {
    regime: len(ccus) for regime, ccus in unresolved.items()
})
