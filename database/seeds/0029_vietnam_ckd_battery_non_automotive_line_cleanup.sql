BEGIN;

-- Vietnam CKD traction-battery data-quality cleanup.
-- 85076031 is the laptop-computer line and 85076032 is the aircraft line.
-- Neither is an automotive traction-battery line for this project's
-- new-passenger-car CKD scope.  Preserve the rows for auditability, but keep
-- them out of active tariff matching by suspending them.  The predicate is
-- intentionally limited to this CCU and these two national codes.

WITH doc AS (
  SELECT source_document_id
  FROM evidence.source_document
  WHERE source_code = 'VN-DECREE-118-2022-ACFTA'
)
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary, extraction_method,
  extracted_at, verification_status
)
SELECT
  'VN-CKD-BATTERY-AUTO-SCOPE-EXCLUDE-85076031-32',
  doc.source_document_id,
  'tariff_line',
  'ACFTA Appendix / 8507.60.31 and 8507.60.32',
  '8507.60.31: lithium-ion accumulators for laptop computers; 8507.60.32: lithium-ion accumulators for aircraft.',
  '8507.60.31：用于笔记本电脑的锂离子蓄电池；8507.60.32：用于航空器的锂离子蓄电池。两者均不属于汽车动力电池用途。',
  'Verified scope exclusion for the new-passenger-car CKD traction-battery CCU. The rows are suspended, not deleted, so their original tariff evidence remains auditable.',
  'official_portal_manual_review',
  TIMESTAMPTZ '2026-08-18 14:00:00+08',
  'VERIFIED'::ref.verification_status
FROM doc
ON CONFLICT (clause_code) DO UPDATE SET
  source_document_id = EXCLUDED.source_document_id,
  locator_type = EXCLUDED.locator_type,
  locator_value = EXCLUDED.locator_value,
  original_text = EXCLUDED.original_text,
  translated_text_cn = EXCLUDED.translated_text_cn,
  evidence_summary = EXCLUDED.evidence_summary,
  extraction_method = EXCLUDED.extraction_method,
  extracted_at = EXCLUDED.extracted_at,
  verification_status = EXCLUDED.verification_status;

WITH cleanup_evidence AS (
  SELECT source_clause_id
  FROM evidence.source_clause
  WHERE clause_code = 'VN-CKD-BATTERY-AUTO-SCOPE-EXCLUDE-85076031-32'
), target AS (
  SELECT
    mapping.mapping_id,
    mapping.source_clause_id AS previous_source_clause_id,
    cleanup_evidence.source_clause_id AS cleanup_source_clause_id
  FROM customs.tariff_mapping AS mapping
  JOIN customs.ccu_candidate_hs AS candidate
    ON candidate.candidate_id = mapping.candidate_id
  JOIN customs.customs_classification_unit AS component
    ON component.ccu_id = candidate.ccu_id
  CROSS JOIN cleanup_evidence
  WHERE component.ccu_code = 'VN-CKD-TRACTION-BATTERY'
    AND mapping.national_tariff_code IN ('85076031','85076032')
    AND mapping.record_status = 'ACTIVE'::ref.record_status
)
UPDATE customs.tariff_mapping AS mapping
SET record_status = 'SUSPENDED'::ref.record_status,
    source_clause_id = target.cleanup_source_clause_id,
    additional_measure = mapping.additional_measure || jsonb_build_object(
      'data_quality_status','SUSPENDED_NON_AUTOMOTIVE_LINE',
      'suspension_reason','明确为笔记本电脑或航空器用途，不属于新乘用车CKD汽车动力电池',
      'suspension_scope','VN-CKD-TRACTION-BATTERY',
      'suspended_tariff_codes',jsonb_build_array('85076031','85076032'),
      'previous_source_clause_id',target.previous_source_clause_id::text,
      'cleanup_seed','0029_vietnam_ckd_battery_non_automotive_line_cleanup',
      'suspended_at','2026-08-18T14:00:00+08:00'
    ),
    eligibility_condition = mapping.eligibility_condition || jsonb_build_object(
      'automotive_scope_excluded',true,
      'non_automotive_use','laptop_or_aircraft',
      'active_matching_excluded',true
    ),
    updated_at = now()
FROM target
WHERE mapping.mapping_id = target.mapping_id;

COMMIT;
