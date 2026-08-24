BEGIN;

CREATE TABLE IF NOT EXISTS rules.vehicle_tax_route (
  vehicle_tax_route_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  route_code text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  decision_order smallint NOT NULL CHECK (decision_order BETWEEN 1 AND 5),
  route_name_cn text NOT NULL,
  route_name_en text NOT NULL,
  route_kind text NOT NULL CHECK (
    route_kind IN (
      'CBU',
      'CKD_WHOLE_KIT',
      'PARTS_SUBASSEMBLIES',
      'PART_LEVEL',
      'MIXED_KD'
    )
  ),
  import_mode ref.import_mode NOT NULL,
  classification_granularity text NOT NULL CHECK (
    classification_granularity IN (
      'FINISHED_VEHICLE',
      'CKD_VEHICLE_TARIFF_LINE',
      'SUBASSEMBLY_TAX_BUCKET',
      'CUSTOMS_CLASSIFICATION_UNIT',
      'MIXED_ROUTE_ALLOCATION'
    )
  ),
  decision_condition jsonb NOT NULL,
  required_input_fields jsonb NOT NULL,
  calculation_dsl jsonb NOT NULL,
  fallback_route_code text,
  decision_note text NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(decision_condition) = 'object'),
  CHECK (jsonb_typeof(required_input_fields) = 'array'),
  CHECK (jsonb_typeof(calculation_dsl) = 'object'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (route_code, version),
  UNIQUE (country_id, decision_order, effective_from, version)
);

CREATE TABLE IF NOT EXISTS rules.vehicle_tax_route_source_link (
  vehicle_tax_route_source_link_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_tax_route_id uuid NOT NULL
    REFERENCES rules.vehicle_tax_route(vehicle_tax_route_id),
  source_clause_id uuid NOT NULL
    REFERENCES evidence.source_clause(source_clause_id),
  source_purpose text NOT NULL,
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (vehicle_tax_route_id, source_clause_id),
  UNIQUE (vehicle_tax_route_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS rules.kd_tax_bucket_definition (
  kd_tax_bucket_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bucket_code text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  bucket_name_cn text NOT NULL,
  bucket_name_en text NOT NULL,
  applicable_route_codes jsonb NOT NULL,
  included_scope jsonb NOT NULL,
  excluded_scope jsonb NOT NULL,
  classification_granularity text NOT NULL,
  import_tax_treatment jsonb NOT NULL,
  local_finished_vehicle_treatment jsonb NOT NULL,
  required_input_fields jsonb NOT NULL,
  double_count_key text NOT NULL,
  source_clause_id uuid REFERENCES evidence.source_clause(source_clause_id),
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(applicable_route_codes) = 'array'),
  CHECK (jsonb_typeof(included_scope) = 'array'),
  CHECK (jsonb_typeof(excluded_scope) = 'array'),
  CHECK (jsonb_typeof(import_tax_treatment) = 'object'),
  CHECK (jsonb_typeof(local_finished_vehicle_treatment) = 'object'),
  CHECK (jsonb_typeof(required_input_fields) = 'array'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (bucket_code, version)
);

CREATE TABLE IF NOT EXISTS customs.vehicle_tariff_rate_line (
  vehicle_tariff_rate_line_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rate_line_code text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  vehicle_tax_route_id uuid NOT NULL
    REFERENCES rules.vehicle_tax_route(vehicle_tax_route_id),
  tariff_schedule_code text NOT NULL,
  tariff_year integer NOT NULL CHECK (tariff_year BETWEEN 2000 AND 2200),
  origin_regime ref.origin_regime NOT NULL,
  trade_agreement_id uuid REFERENCES ref.trade_agreement(trade_agreement_id),
  hs6_code char(6) NOT NULL CHECK (hs6_code ~ '^[0-9]{6}$'),
  national_tariff_code text NOT NULL
    CHECK (national_tariff_code ~ '^[0-9]{10}$'),
  linked_pdk_tariff_code text
    CHECK (
      linked_pdk_tariff_code IS NULL
      OR linked_pdk_tariff_code ~ '^[0-9]{10}$'
    ),
  tariff_description text NOT NULL,
  powertrain ref.powertrain NOT NULL,
  vehicle_category text NOT NULL DEFAULT 'PASSENGER_VEHICLE_8703',
  import_duty_rate numeric(12,8)
    CHECK (import_duty_rate IS NULL OR import_duty_rate >= 0),
  sales_tax_rate numeric(12,8)
    CHECK (sales_tax_rate IS NULL OR sales_tax_rate >= 0),
  excise_duty_rate numeric(12,8)
    CHECK (excise_duty_rate IS NULL OR excise_duty_rate >= 0),
  sales_tax_treatment text NOT NULL CHECK (
    sales_tax_treatment IN ('TAXABLE', 'EXEMPT', 'UNKNOWN')
  ),
  excise_treatment text NOT NULL CHECK (
    excise_treatment IN (
      'STATUTORY_RATE',
      'NOT_AT_IMPORT',
      'REQUIRES_PDK_CORRELATION',
      'UNKNOWN'
    )
  ),
  eligibility_condition jsonb NOT NULL DEFAULT '{}'::jsonb,
  tariff_source_clause_id uuid NOT NULL
    REFERENCES evidence.source_clause(source_clause_id),
  tax_treatment_source_clause_id uuid
    REFERENCES evidence.source_clause(source_clause_id),
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  route_verification_status ref.verification_status NOT NULL
    DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(eligibility_condition) = 'object'),
  CHECK (origin_regime <> 'FTA' OR trade_agreement_id IS NOT NULL),
  CHECK (origin_regime = 'FTA' OR trade_agreement_id IS NULL),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (rate_line_code, version)
);

CREATE INDEX IF NOT EXISTS idx_vehicle_tax_route_lookup
  ON rules.vehicle_tax_route(
    country_id, decision_order, effective_from, effective_to
  );

CREATE INDEX IF NOT EXISTS idx_kd_tax_bucket_lookup
  ON rules.kd_tax_bucket_definition(
    country_id, effective_from, effective_to
  );

CREATE INDEX IF NOT EXISTS idx_vehicle_tariff_rate_lookup
  ON customs.vehicle_tariff_rate_line(
    country_id, vehicle_tax_route_id, powertrain, origin_regime,
    tariff_year, effective_from, effective_to
  );

CREATE INDEX IF NOT EXISTS idx_vehicle_tariff_rate_code
  ON customs.vehicle_tariff_rate_line(
    national_tariff_code, tariff_schedule_code, tariff_year
  );

CREATE OR REPLACE VIEW ai.v_malaysia_five_route_decision_current AS
SELECT
  route.decision_order,
  route.route_code,
  route.route_name_cn,
  route.route_name_en,
  route.route_kind,
  route.import_mode,
  route.classification_granularity,
  route.decision_condition,
  route.required_input_fields,
  route.fallback_route_code,
  route.decision_note,
  route.effective_from,
  route.effective_to,
  route.verification_status
FROM rules.vehicle_tax_route route
JOIN ref.country country ON country.country_id = route.country_id
WHERE country.iso2 = 'MY'
  AND route.record_status = 'ACTIVE'
  AND route.effective_from <= current_date
  AND (route.effective_to IS NULL OR route.effective_to > current_date);

CREATE OR REPLACE VIEW ai.v_malaysia_vehicle_tariff_rates_current AS
SELECT
  route.decision_order,
  route.route_code,
  route.route_kind,
  line.tariff_schedule_code,
  line.tariff_year,
  line.origin_regime,
  agreement.agreement_code,
  line.hs6_code,
  line.national_tariff_code,
  line.linked_pdk_tariff_code,
  line.tariff_description,
  line.powertrain,
  line.import_duty_rate,
  line.sales_tax_rate,
  line.excise_duty_rate,
  line.sales_tax_treatment,
  line.excise_treatment,
  line.eligibility_condition,
  line.verification_status,
  line.route_verification_status,
  source.source_code,
  clause.locator_value AS source_locator,
  line.effective_from,
  line.effective_to
FROM customs.vehicle_tariff_rate_line line
JOIN rules.vehicle_tax_route route
  ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
JOIN ref.country country ON country.country_id = line.country_id
LEFT JOIN ref.trade_agreement agreement
  ON agreement.trade_agreement_id = line.trade_agreement_id
JOIN evidence.source_clause clause
  ON clause.source_clause_id = line.tariff_source_clause_id
JOIN evidence.source_document source
  ON source.source_document_id = clause.source_document_id
WHERE country.iso2 = 'MY'
  AND line.record_status = 'ACTIVE'
  AND line.effective_from <= current_date
  AND (line.effective_to IS NULL OR line.effective_to > current_date);

CREATE OR REPLACE VIEW ai.v_malaysia_five_route_readiness AS
SELECT
  route.decision_order,
  route.route_code,
  route.route_name_cn,
  route.verification_status AS route_verification_status,
  count(line.vehicle_tariff_rate_line_id) AS tariff_line_count,
  count(*) FILTER (WHERE line.origin_regime = 'MFN') AS mfn_line_count,
  count(*) FILTER (
    WHERE agreement.agreement_code = 'ACFTA'
  ) AS acfta_line_count,
  count(*) FILTER (
    WHERE agreement.agreement_code = 'RCEP'
  ) AS rcep_line_count,
  count(*) FILTER (
    WHERE line.vehicle_tariff_rate_line_id IS NOT NULL
      AND line.import_duty_rate IS NULL
  ) AS missing_public_duty_rate_count,
  count(*) FILTER (
    WHERE line.verification_status = 'VERIFIED'
  ) AS verified_tariff_line_count,
  CASE
    WHEN route.route_kind IN (
      'PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD'
    ) THEN (
      SELECT count(*)
      FROM rules.kd_tax_bucket_definition bucket
      WHERE bucket.country_id = route.country_id
        AND bucket.record_status = 'ACTIVE'
    )
    ELSE 0
  END AS kd_tax_bucket_count,
  CASE
    WHEN route.route_kind IN (
      'PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD'
    ) THEN (
      SELECT count(*)
      FROM customs.customs_classification_unit ccu
      WHERE ccu.unit_level = 'CUSTOMS_CLASSIFICATION_UNIT'
        AND ccu.record_status = 'ACTIVE'
    )
    ELSE 0
  END AS active_ccu_count,
  CASE
    WHEN route.route_kind IN (
      'PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD'
    ) THEN (
      SELECT count(DISTINCT candidate.ccu_id)
      FROM customs.tariff_mapping mapping
      JOIN customs.ccu_candidate_hs candidate
        ON candidate.candidate_id = mapping.candidate_id
      WHERE mapping.country_id = route.country_id
        AND mapping.record_status = 'ACTIVE'
    )
    ELSE 0
  END AS mapped_ccu_count,
  CASE
    WHEN route.route_kind IN (
      'PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD'
    ) THEN (
      SELECT count(*)
      FROM customs.tariff_mapping mapping
      WHERE mapping.country_id = route.country_id
        AND mapping.record_status = 'ACTIVE'
    )
    ELSE 0
  END AS ccu_tariff_mapping_count,
  CASE
    WHEN route.route_kind IN (
      'PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD'
    ) THEN (
      SELECT count(*)
      FROM customs.tariff_mapping mapping
      WHERE mapping.country_id = route.country_id
        AND mapping.record_status = 'ACTIVE'
        AND mapping.duty_rate IS NULL
    )
    ELSE 0
  END AS ccu_mapping_missing_duty_count
FROM rules.vehicle_tax_route route
JOIN ref.country country ON country.country_id = route.country_id
LEFT JOIN customs.vehicle_tariff_rate_line line
  ON line.vehicle_tax_route_id = route.vehicle_tax_route_id
  AND line.record_status = 'ACTIVE'
LEFT JOIN ref.trade_agreement agreement
  ON agreement.trade_agreement_id = line.trade_agreement_id
WHERE country.iso2 = 'MY'
  AND route.record_status = 'ACTIVE'
GROUP BY
  route.decision_order,
  route.route_code,
  route.route_name_cn,
  route.route_kind,
  route.country_id,
  route.verification_status;

COMMIT;
