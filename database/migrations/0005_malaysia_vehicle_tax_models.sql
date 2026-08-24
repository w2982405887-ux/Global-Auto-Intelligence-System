BEGIN;

CREATE TABLE IF NOT EXISTS customs.vehicle_tariff_line (
  vehicle_tariff_line_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  line_code text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  tariff_version text NOT NULL,
  hs6_code char(6) NOT NULL CHECK (hs6_code ~ '^[0-9]{6}$'),
  national_tariff_code text NOT NULL CHECK (national_tariff_code ~ '^[0-9]{10}$'),
  tariff_description text NOT NULL,
  import_mode ref.import_mode NOT NULL DEFAULT 'CBU',
  origin_regime ref.origin_regime NOT NULL DEFAULT 'MFN',
  powertrain ref.powertrain NOT NULL,
  vehicle_category text NOT NULL DEFAULT 'PASSENGER_VEHICLE_8703',
  classification_inputs jsonb NOT NULL DEFAULT '{}'::jsonb,
  import_duty_rate numeric(12,8) NOT NULL CHECK (import_duty_rate >= 0),
  excise_duty_rate numeric(12,8) NOT NULL CHECK (excise_duty_rate >= 0),
  sales_tax_rate numeric(12,8) NOT NULL CHECK (sales_tax_rate >= 0),
  tax_sequence jsonb NOT NULL,
  tariff_source_clause_id uuid NOT NULL
    REFERENCES evidence.source_clause(source_clause_id),
  excise_source_clause_id uuid NOT NULL
    REFERENCES evidence.source_clause(source_clause_id),
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  classification_verification_status ref.verification_status NOT NULL
    DEFAULT 'CANDIDATE',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(classification_inputs) = 'object'),
  CHECK (jsonb_typeof(tax_sequence) = 'array'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (line_code, version),
  UNIQUE (
    country_id, tariff_version, national_tariff_code, origin_regime,
    effective_from, version
  )
);

CREATE TABLE IF NOT EXISTS rules.automotive_incentive_program (
  incentive_program_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  program_code text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  program_name_cn text NOT NULL,
  import_mode ref.import_mode,
  powertrain ref.powertrain,
  incentive_scope text NOT NULL,
  condition_expression jsonb NOT NULL,
  benefit_expression jsonb NOT NULL,
  approval_required boolean NOT NULL DEFAULT true,
  approval_authority_id uuid REFERENCES ref.authority(authority_id),
  source_clause_id uuid NOT NULL REFERENCES evidence.source_clause(source_clause_id),
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(condition_expression) = 'object'),
  CHECK (jsonb_typeof(benefit_expression) = 'object'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (program_code, version)
);

CREATE TABLE IF NOT EXISTS enterprise.vehicle_project_approval (
  vehicle_project_approval_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id uuid REFERENCES enterprise.vehicle_model(vehicle_id),
  incentive_program_id uuid NOT NULL
    REFERENCES rules.automotive_incentive_program(incentive_program_id),
  enterprise_code text NOT NULL,
  approval_reference text,
  approval_status ref.review_decision NOT NULL DEFAULT 'PENDING',
  approved_condition_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  approved_benefit_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  evidence_source_document_id uuid
    REFERENCES evidence.source_document(source_document_id),
  effective_from date,
  effective_to date,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(approved_condition_payload) = 'object'),
  CHECK (jsonb_typeof(approved_benefit_payload) = 'object'),
  CHECK (effective_from IS NULL OR effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (enterprise_code, incentive_program_id, approval_reference)
);

CREATE INDEX IF NOT EXISTS idx_vehicle_tariff_lookup
  ON customs.vehicle_tariff_line(
    country_id, import_mode, powertrain, origin_regime,
    effective_from, effective_to
  );

CREATE INDEX IF NOT EXISTS idx_automotive_incentive_lookup
  ON rules.automotive_incentive_program(
    country_id, import_mode, powertrain, effective_from, effective_to
  );

CREATE OR REPLACE VIEW ai.v_malaysia_vehicle_tax_lines_current AS
SELECT
  line.line_code,
  line.hs6_code,
  line.national_tariff_code,
  line.tariff_description,
  line.import_mode,
  line.powertrain,
  line.vehicle_category,
  line.classification_inputs,
  line.import_duty_rate,
  line.excise_duty_rate,
  line.sales_tax_rate,
  line.tax_sequence,
  line.effective_from,
  line.effective_to,
  line.verification_status,
  line.classification_verification_status,
  tariff_source.source_code AS tariff_source_code,
  tariff_clause.locator_value AS tariff_source_locator,
  excise_source.source_code AS excise_source_code,
  excise_clause.locator_value AS excise_source_locator
FROM customs.vehicle_tariff_line line
JOIN ref.country country ON country.country_id = line.country_id
JOIN evidence.source_clause tariff_clause
  ON tariff_clause.source_clause_id = line.tariff_source_clause_id
JOIN evidence.source_document tariff_source
  ON tariff_source.source_document_id = tariff_clause.source_document_id
JOIN evidence.source_clause excise_clause
  ON excise_clause.source_clause_id = line.excise_source_clause_id
JOIN evidence.source_document excise_source
  ON excise_source.source_document_id = excise_clause.source_document_id
WHERE country.iso2 = 'MY'
  AND line.record_status = 'ACTIVE'
  AND line.effective_from <= current_date
  AND (line.effective_to IS NULL OR line.effective_to > current_date);

CREATE OR REPLACE VIEW ai.v_malaysia_automotive_incentives_current AS
SELECT
  program.program_code,
  program.program_name_cn,
  program.import_mode,
  program.powertrain,
  program.incentive_scope,
  program.condition_expression,
  program.benefit_expression,
  program.approval_required,
  authority.authority_code,
  authority.authority_name,
  program.effective_from,
  program.effective_to,
  program.verification_status,
  source.source_code,
  clause.locator_value AS source_locator
FROM rules.automotive_incentive_program program
JOIN ref.country country ON country.country_id = program.country_id
LEFT JOIN ref.authority authority
  ON authority.authority_id = program.approval_authority_id
JOIN evidence.source_clause clause
  ON clause.source_clause_id = program.source_clause_id
JOIN evidence.source_document source
  ON source.source_document_id = clause.source_document_id
WHERE country.iso2 = 'MY'
  AND program.record_status = 'ACTIVE'
  AND program.effective_from <= current_date
  AND (program.effective_to IS NULL OR program.effective_to > current_date);

CREATE OR REPLACE VIEW ai.v_malaysia_vehicle_scenarios_current AS
SELECT
  scenario.scenario_code,
  scenario.scenario_name_cn,
  scenario.import_mode,
  scenario.powertrain,
  scenario.classification_route,
  scenario.required_input_fields,
  scenario.output_scope,
  scenario.effective_from,
  scenario.effective_to,
  scenario.verification_status
FROM rules.tax_scenario_model scenario
JOIN ref.country country ON country.country_id = scenario.country_id
WHERE country.iso2 = 'MY'
  AND scenario.record_status = 'ACTIVE'
  AND scenario.effective_from <= current_date
  AND (scenario.effective_to IS NULL OR scenario.effective_to > current_date)
  AND (
    scenario.scenario_code LIKE 'SCN-MY-CBU-%-2025'
    OR scenario.scenario_code LIKE 'SCN-MY-LOCAL-%'
  );

COMMIT;
