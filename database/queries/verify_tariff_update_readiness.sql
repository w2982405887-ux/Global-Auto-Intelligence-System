\pset null '[NULL]'
\pset expanded off

\echo '1. Effective tariff inventory by regime, version and quality'
SELECT
  COALESCE(agreement.agreement_code, 'MFN') AS regime,
  mapping.tariff_version,
  mapping.verification_status,
  count(*) AS mapping_count,
  min(mapping.effective_from) AS earliest_effective_from,
  max(mapping.effective_to) AS latest_effective_to
FROM customs.tariff_mapping mapping
LEFT JOIN ref.trade_agreement agreement
  ON agreement.trade_agreement_id = mapping.trade_agreement_id
WHERE mapping.record_status = 'ACTIVE'
GROUP BY
  COALESCE(agreement.agreement_code, 'MFN'),
  mapping.tariff_version,
  mapping.verification_status
ORDER BY regime, mapping.tariff_version, mapping.verification_status;

\echo '2. Data-quality exceptions requiring correction'
SELECT
  mapping.mapping_code,
  mapping.record_status,
  mapping.verification_status,
  mapping.duty_rate,
  mapping.effective_from,
  mapping.effective_to,
  source.source_code,
  source.content_sha256,
  source.archived_object_key,
  CASE
    WHEN mapping.duty_rate IS NULL THEN 'MISSING_DUTY_RATE'
    WHEN mapping.verification_status IN ('VERIFIED','RULING_CONFIRMED')
      AND mapping.record_status = 'DRAFT' THEN 'VERIFIED_BUT_NOT_PUBLISHED'
    WHEN mapping.record_status = 'ACTIVE'
      AND mapping.effective_to IS NOT NULL
      AND mapping.effective_to <= current_date THEN 'ACTIVE_BUT_EXPIRED'
    WHEN source.content_sha256 IS NULL THEN 'SOURCE_HASH_MISSING'
    WHEN source.archived_object_key IS NULL THEN 'SOURCE_ARCHIVE_MISSING'
  END AS exception_type
FROM customs.tariff_mapping mapping
JOIN evidence.source_clause clause
  ON clause.source_clause_id = mapping.source_clause_id
JOIN evidence.source_document source
  ON source.source_document_id = clause.source_document_id
WHERE mapping.duty_rate IS NULL
   OR (
     mapping.verification_status IN ('VERIFIED','RULING_CONFIRMED')
     AND mapping.record_status = 'DRAFT'
   )
   OR (
     mapping.record_status = 'ACTIVE'
     AND mapping.effective_to IS NOT NULL
     AND mapping.effective_to <= current_date
   )
   OR source.content_sha256 IS NULL
   OR source.archived_object_key IS NULL
ORDER BY exception_type, mapping.mapping_code;

\echo '3. Active mappings requiring classification or authority follow-up'
SELECT
  COALESCE(agreement.agreement_code, 'MFN') AS regime,
  ccu.ccu_code,
  mapping.mapping_code,
  mapping.national_tariff_code,
  mapping.verification_status,
  mapping.additional_measure->>'classification_link_status'
    AS classification_link_status,
  mapping.additional_measure->'nomenclature_correlation'->>'status'
    AS nomenclature_correlation_status
FROM customs.tariff_mapping mapping
JOIN customs.ccu_candidate_hs candidate
  ON candidate.candidate_id = mapping.candidate_id
JOIN customs.customs_classification_unit ccu
  ON ccu.ccu_id = candidate.ccu_id
LEFT JOIN ref.trade_agreement agreement
  ON agreement.trade_agreement_id = mapping.trade_agreement_id
WHERE mapping.record_status = 'ACTIVE'
  AND (
    mapping.verification_status IN ('UNVERIFIED','CANDIDATE')
    OR mapping.additional_measure->>'classification_link_status' = 'CANDIDATE'
    OR mapping.additional_measure->'nomenclature_correlation'->>'status' = 'REQUIRED'
  )
ORDER BY regime, ccu.ccu_code, mapping.mapping_code;

\echo '4. Source refresh queue'
SELECT
  source.source_code,
  source.document_title,
  source.official_status,
  source.effective_from,
  source.effective_to,
  source.accessed_at::date AS last_accessed_date,
  (current_date - source.accessed_at::date) AS days_since_access,
  count(DISTINCT mapping.mapping_id) AS linked_tariff_mappings,
  CASE
    WHEN source.effective_to IS NOT NULL
      AND source.effective_to <= current_date THEN 'EXPIRED'
    WHEN source.effective_to IS NOT NULL
      AND source.effective_to <= current_date + 90 THEN 'EXPIRING_WITHIN_90_DAYS'
    WHEN current_date - source.accessed_at::date >= 180 THEN 'REFRESH_DUE'
    ELSE 'CURRENT'
  END AS refresh_status
FROM evidence.source_document source
LEFT JOIN evidence.source_clause clause
  ON clause.source_document_id = source.source_document_id
LEFT JOIN customs.tariff_mapping mapping
  ON mapping.source_clause_id = clause.source_clause_id
WHERE mapping.mapping_id IS NOT NULL
GROUP BY source.source_document_id
ORDER BY
  CASE
    WHEN source.effective_to IS NOT NULL
      AND source.effective_to <= current_date THEN 1
    WHEN source.effective_to IS NOT NULL
      AND source.effective_to <= current_date + 90 THEN 2
    WHEN current_date - source.accessed_at::date >= 180 THEN 3
    ELSE 4
  END,
  source.source_code;

\echo '5. Open high-priority gaps'
SELECT
  priority,
  status,
  blocking_scope,
  field_path,
  description,
  next_action
FROM audit.missing_data
WHERE priority = 'P0'
  AND status NOT IN ('RESOLVED','WAIVED')
ORDER BY status, blocking_scope, field_path;
