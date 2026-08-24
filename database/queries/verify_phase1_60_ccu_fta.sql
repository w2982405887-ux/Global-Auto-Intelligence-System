\pset null '[NULL]'

WITH ccu AS (
  SELECT c.ccu_id, c.ccu_code
  FROM customs.customs_classification_unit c
  WHERE c.unit_level='CUSTOMS_CLASSIFICATION_UNIT'
    AND c.record_status='ACTIVE'
),
coverage AS (
  SELECT c.ccu_id, c.ccu_code,
    count(DISTINCT m.mapping_id) FILTER (
      WHERE m.origin_regime='MFN' AND m.record_status='ACTIVE'
    ) AS mfn_count,
    count(DISTINCT m.mapping_id) FILTER (
      WHERE ta.agreement_code='ACFTA' AND m.record_status='ACTIVE'
    ) AS acfta_count,
    count(DISTINCT m.mapping_id) FILTER (
      WHERE ta.agreement_code='RCEP' AND m.record_status='ACTIVE'
    ) AS rcep_count
  FROM ccu c
  LEFT JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
  LEFT JOIN customs.tariff_mapping m ON m.candidate_id=h.candidate_id
  LEFT JOIN ref.trade_agreement ta
    ON ta.trade_agreement_id=m.trade_agreement_id
  GROUP BY c.ccu_id,c.ccu_code
)
SELECT count(*) AS active_ccus,
       count(*) FILTER(WHERE mfn_count>0) AS mfn_covered,
       count(*) FILTER(WHERE acfta_count>0) AS acfta_covered,
       count(*) FILTER(WHERE rcep_count>0) AS rcep_covered,
       count(*) FILTER(
         WHERE mfn_count>0 AND acfta_count>0 AND rcep_count>0
       ) AS all_three_regimes
FROM coverage;

SELECT ta.agreement_code, m.verification_status,
       count(*) AS mapping_count, count(DISTINCT c.ccu_id) AS ccu_count,
       min(m.duty_rate) AS minimum_rate,
       max(m.duty_rate) AS maximum_rate
FROM customs.tariff_mapping m
JOIN ref.trade_agreement ta
  ON ta.trade_agreement_id=m.trade_agreement_id
JOIN customs.ccu_candidate_hs h ON h.candidate_id=m.candidate_id
JOIN customs.customs_classification_unit c ON c.ccu_id=h.ccu_id
WHERE m.origin_regime='FTA' AND m.record_status='ACTIVE'
GROUP BY ta.agreement_code,m.verification_status
ORDER BY ta.agreement_code,m.verification_status;

SELECT
  count(*) AS phase18_mapping_count,
  count(*) FILTER (WHERE m.duty_rate IS NULL) AS missing_rate,
  count(*) FILTER (WHERE m.source_clause_id IS NULL) AS missing_clause,
  count(*) FILTER (
    WHERE d.content_sha256 IS NULL OR d.archived_object_key IS NULL
  ) AS missing_source_archive,
  count(*) FILTER (
    WHERE m.eligibility_condition
      ->>'preferential_rate_requires_verified_origin' <> 'true'
  ) AS missing_origin_gate,
  count(*) FILTER (
    WHERE m.eligibility_condition->>'fallback_regime' <> 'MFN'
  ) AS missing_mfn_fallback
FROM customs.tariff_mapping m
JOIN evidence.source_clause clause
  ON clause.source_clause_id=m.source_clause_id
JOIN evidence.source_document d
  ON d.source_document_id=clause.source_document_id
WHERE m.mapping_code LIKE 'MAP-MY-ACFTA-2026-%'
   OR m.mapping_code LIKE 'MAP-MY-RCEP-2026-%';

WITH ccu AS (
  SELECT c.ccu_id,c.ccu_code
  FROM customs.customs_classification_unit c
  WHERE c.unit_level='CUSTOMS_CLASSIFICATION_UNIT'
    AND c.record_status='ACTIVE'
),
coverage AS (
  SELECT c.ccu_code,
    count(m.mapping_id) FILTER (
      WHERE ta.agreement_code='ACFTA' AND m.record_status='ACTIVE'
    ) AS acfta_count,
    count(m.mapping_id) FILTER (
      WHERE ta.agreement_code='RCEP' AND m.record_status='ACTIVE'
    ) AS rcep_count
  FROM ccu c
  LEFT JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
  LEFT JOIN customs.tariff_mapping m ON m.candidate_id=h.candidate_id
  LEFT JOIN ref.trade_agreement ta
    ON ta.trade_agreement_id=m.trade_agreement_id
  GROUP BY c.ccu_code
)
SELECT * FROM coverage
WHERE acfta_count=0 OR rcep_count=0
ORDER BY ccu_code;

SELECT field_path, priority, status, blocking_scope
FROM audit.missing_data
WHERE field_path LIKE 'customs.tariff_mapping[ACFTA]%'
   OR field_path LIKE 'customs.tariff_mapping[RCEP]%'
ORDER BY field_path;

