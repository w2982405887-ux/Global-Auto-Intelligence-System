BEGIN;

-- Passenger-vehicle scope cleanup (2026-08-12).
-- Business scope: new passenger cars/SUVs (heading 87.03) and their
-- applicable major components.  We deliberately keep rows that mention
-- 87.03 together with other headings, because those are shared component
-- classifications and remain usable for passenger vehicles.
--
-- This migration uses REJECTED rather than physical DELETE.  Existing
-- calculation/audit tables reference tariff_mapping rows, so logical
-- rejection preserves referential integrity and makes the cleanup reversible.

CREATE TABLE IF NOT EXISTS audit.passenger_vehicle_scope_cleanup_20260812 (
  mapping_id uuid PRIMARY KEY,
  country_iso2 char(2) NOT NULL,
  ccu_code text NOT NULL,
  national_tariff_code text NOT NULL,
  tariff_description text,
  previous_record_status ref.record_status NOT NULL,
  cleanup_reason text NOT NULL,
  cleaned_at timestamptz NOT NULL DEFAULT now()
);

WITH candidates AS (
  SELECT
    m.mapping_id,
    c.iso2,
    ccu.ccu_code,
    m.national_tariff_code,
    m.tariff_description,
    upper(coalesce(m.tariff_description, '')) AS d,
    CASE
      WHEN upper(coalesce(m.tariff_description, '')) LIKE '%87.02, 87%'
        THEN 'SCOPE_NOT_VERIFIABLE_SOURCE_TEXT'
      WHEN upper(coalesce(m.tariff_description, '')) LIKE '%TRACTOR%'
        OR upper(coalesce(m.tariff_description, '')) LIKE '%MÁY KÉO%'
        OR upper(coalesce(m.tariff_description, '')) LIKE '%MOTORCYCLE%'
        OR upper(coalesce(m.tariff_description, '')) LIKE '%MOTOR CYCLE%'
        OR upper(coalesce(m.tariff_description, '')) LIKE '%MÔ TÔ%'
        OR upper(coalesce(m.tariff_description, '')) LIKE '%XE MÁY%'
        THEN 'EXPLICIT_NON_PASSENGER_VEHICLE'
      WHEN upper(coalesce(m.tariff_description, '')) ~ '87[.]0[1245]([^0-9]|$)'
        OR upper(coalesce(m.tariff_description, '')) ~ '87[.]11([^0-9]|$)'
        OR upper(coalesce(m.tariff_description, '')) ~ '88[.]'
        OR upper(coalesce(m.tariff_description, '')) LIKE '%AIRCRAFT%'
        OR upper(coalesce(m.tariff_description, '')) LIKE '%HELICOPTER%'
        THEN 'EXPLICIT_NON_PASSENGER_HEADING'
      ELSE NULL
    END AS cleanup_reason
  FROM customs.tariff_mapping m
  JOIN ref.country c ON c.country_id = m.country_id
  JOIN customs.ccu_candidate_hs h ON h.candidate_id = m.candidate_id
  JOIN customs.customs_classification_unit ccu ON ccu.ccu_id = h.ccu_id
  WHERE m.record_status = 'ACTIVE'
    AND c.iso2 IN ('MY', 'VN')
    -- A shared line that explicitly includes 87.03 remains in scope.
    AND upper(coalesce(m.tariff_description, '')) !~ '87[.]03([^0-9]|$)'
    AND (
      upper(coalesce(m.tariff_description, '')) LIKE '%TRACTOR%'
      OR upper(coalesce(m.tariff_description, '')) LIKE '%MÁY KÉO%'
      OR upper(coalesce(m.tariff_description, '')) LIKE '%MOTORCYCLE%'
      OR upper(coalesce(m.tariff_description, '')) LIKE '%MOTOR CYCLE%'
      OR upper(coalesce(m.tariff_description, '')) LIKE '%MÔ TÔ%'
      OR upper(coalesce(m.tariff_description, '')) LIKE '%XE MÁY%'
      OR upper(coalesce(m.tariff_description, '')) LIKE '%87.02, 87%'
      OR upper(coalesce(m.tariff_description, '')) ~ '87[.]0[1245]([^0-9]|$)'
      OR upper(coalesce(m.tariff_description, '')) ~ '87[.]11([^0-9]|$)'
      OR upper(coalesce(m.tariff_description, '')) ~ '88[.]'
      OR upper(coalesce(m.tariff_description, '')) LIKE '%AIRCRAFT%'
      OR upper(coalesce(m.tariff_description, '')) LIKE '%HELICOPTER%'
    )
), captured AS (
  INSERT INTO audit.passenger_vehicle_scope_cleanup_20260812 (
    mapping_id, country_iso2, ccu_code, national_tariff_code,
    tariff_description, previous_record_status, cleanup_reason
  )
  SELECT mapping_id, iso2, ccu_code, national_tariff_code,
         tariff_description, 'ACTIVE'::ref.record_status, cleanup_reason
  FROM candidates
  WHERE cleanup_reason IS NOT NULL
  ON CONFLICT (mapping_id) DO NOTHING
  RETURNING mapping_id
)
UPDATE customs.tariff_mapping m
SET record_status = 'REJECTED'::ref.record_status,
    updated_at = now()
FROM audit.passenger_vehicle_scope_cleanup_20260812 a
WHERE a.mapping_id = m.mapping_id
  AND m.record_status = 'ACTIVE'::ref.record_status;

COMMIT;
