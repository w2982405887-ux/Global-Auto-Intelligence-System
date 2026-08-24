BEGIN;

-- One canonical key is required for update comparisons and coverage queries.
-- This changes only the version label; rates, dates and legal evidence remain
-- unchanged.
UPDATE customs.tariff_mapping
SET tariff_version='PDK 2025',
    updated_at=now()
WHERE tariff_version='PDK-2025';

UPDATE rules.country_rule_card
SET tariff_version='PDK 2025',
    updated_at=now()
WHERE tariff_version='PDK-2025';

COMMIT;
