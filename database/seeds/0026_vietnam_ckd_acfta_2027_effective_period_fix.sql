-- Vietnam CKD major-parts: correct the ACFTA effective period.
-- Source: Decree 118/2022/ND-CP, ACFTA schedule column "2022-2027".
-- The source rate is one rate for the whole period through 31 Dec 2027.
-- Existing records were accidentally closed at 2027-01-01, excluding all of 2027.

BEGIN;

UPDATE customs.tariff_mapping AS mapping
SET effective_to = DATE '2028-01-01'
FROM ref.country AS country, ref.trade_agreement AS agreement
WHERE mapping.country_id = country.country_id
  AND mapping.trade_agreement_id = agreement.trade_agreement_id
  AND country.iso2 = 'VN'
  AND agreement.agreement_code = 'ACFTA'
  AND mapping.record_status = 'ACTIVE'
  AND mapping.effective_from = DATE '2026-01-01'
  AND mapping.effective_to = DATE '2027-01-01';

COMMIT;
