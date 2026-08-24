-- Vietnam CKD traction-battery verification query.
-- effective_to is exclusive, so both dates below must return all three
-- regimes for each of the three candidate national tariff lines.
WITH input_dates(as_of) AS (
  VALUES (DATE '2027-01-01'), (DATE '2027-12-31')
)
SELECT
  input_dates.as_of,
  COALESCE(agreement.agreement_code, 'MFN') AS regime,
  mapping.national_tariff_code,
  mapping.duty_rate,
  mapping.effective_from,
  mapping.effective_to,
  mapping.verification_status,
  source_document.official_status,
  source_document.canonical_url,
  source_clause.clause_code
FROM input_dates
JOIN customs.tariff_mapping AS mapping
  ON mapping.effective_from <= input_dates.as_of
 AND (mapping.effective_to IS NULL OR mapping.effective_to > input_dates.as_of)
JOIN ref.country AS country
  ON country.country_id = mapping.country_id
 AND country.iso2 = 'VN'
JOIN customs.ccu_candidate_hs AS candidate
  ON candidate.candidate_id = mapping.candidate_id
 AND candidate.hs6_code = '850760'
JOIN customs.customs_classification_unit AS component
  ON component.ccu_id = candidate.ccu_id
 AND component.ccu_code = 'VN-CKD-TRACTION-BATTERY'
LEFT JOIN ref.trade_agreement AS agreement
  ON agreement.trade_agreement_id = mapping.trade_agreement_id
JOIN evidence.source_clause AS source_clause
  ON source_clause.source_clause_id = mapping.source_clause_id
JOIN evidence.source_document AS source_document
  ON source_document.source_document_id = source_clause.source_document_id
WHERE mapping.national_tariff_code IN ('85076033', '85076039', '85076090')
  AND mapping.record_status = 'ACTIVE'
ORDER BY input_dates.as_of, mapping.national_tariff_code, regime;
