BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS evidence;
CREATE SCHEMA IF NOT EXISTS rules;
CREATE SCHEMA IF NOT EXISTS customs;
CREATE SCHEMA IF NOT EXISTS enterprise;
CREATE SCHEMA IF NOT EXISTS calc;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS ai;

CREATE TYPE ref.record_status AS ENUM
  ('DRAFT', 'ACTIVE', 'SUSPENDED', 'SUPERSEDED', 'EXPIRED', 'REJECTED');
CREATE TYPE ref.verification_status AS ENUM
  ('UNVERIFIED', 'CANDIDATE', 'VERIFIED', 'RULING_CONFIRMED');
CREATE TYPE ref.requirement_type AS ENUM
  ('MANDATORY', 'INCENTIVE_ONLY', 'RULING_RECOMMENDED');
CREATE TYPE ref.import_mode AS ENUM
  ('CBU', 'DKD', 'SKD', 'CKD', 'PARTS', 'LOCAL_PRODUCTION');
CREATE TYPE ref.powertrain AS ENUM
  ('ICE_GASOLINE', 'ICE_DIESEL', 'HEV', 'PHEV', 'EREV', 'BEV', 'FCEV', 'OTHER');
CREATE TYPE ref.ccu_unit_level AS ENUM
  ('VEHICLE_SYSTEM', 'ASSEMBLY', 'SUBASSEMBLY', 'CUSTOMS_CLASSIFICATION_UNIT');
CREATE TYPE ref.assembly_state AS ENUM
  ('COMPLETE', 'INCOMPLETE', 'UNASSEMBLED', 'DISASSEMBLED', 'MIXED', 'UNKNOWN');
CREATE TYPE ref.origin_regime AS ENUM
  ('MFN', 'FTA', 'PREFERENTIAL_PROGRAM', 'ENTERPRISE_EXEMPTION', 'UNKNOWN');
CREATE TYPE ref.rate_type AS ENUM
  ('AD_VALOREM', 'SPECIFIC', 'COMPOUND', 'FORMULA', 'ZERO', 'NOT_APPLICABLE', 'UNKNOWN');
CREATE TYPE ref.rule_domain AS ENUM
  ('CUSTOMS_CLASSIFICATION', 'IMPORT_DUTY', 'SALES_TAX', 'EXCISE', 'VAT_GST',
   'FTA', 'APPROVAL', 'QUOTA', 'LOCALIZATION', 'INCENTIVE', 'VALUATION', 'OTHER');
CREATE TYPE ref.source_type AS ENUM
  ('LAW', 'REGULATION', 'GAZETTE', 'TARIFF_SCHEDULE', 'OFFICIAL_GUIDE',
   'OFFICIAL_PORTAL', 'BUDGET_DOCUMENT', 'ADVANCE_RULING',
   'ENTERPRISE_APPROVAL', 'TREATY', 'OTHER');
CREATE TYPE ref.official_status AS ENUM
  ('OFFICIAL', 'OFFICIAL_ARCHIVE', 'SECONDARY', 'ENTERPRISE_INTERNAL', 'UNKNOWN');
CREATE TYPE ref.calculation_status AS ENUM
  ('QUEUED', 'RUNNING', 'COMPLETE', 'PARTIAL', 'BLOCKED', 'FAILED', 'SUPERSEDED');
CREATE TYPE ref.completeness AS ENUM ('COMPLETE', 'PARTIAL', 'BLOCKED');
CREATE TYPE ref.missing_data_kind AS ENUM
  ('PUBLIC_RESEARCH', 'ENTERPRISE_INPUT', 'AUTHORITY_CONFIRMATION',
   'ADVANCE_RULING', 'OFFICIAL_NOT_FOUND');
CREATE TYPE ref.data_ownership AS ENUM ('PUBLIC', 'ENTERPRISE', 'MIXED');
CREATE TYPE ref.missing_data_status AS ENUM
  ('OPEN', 'IN_RESEARCH', 'WAITING_ENTERPRISE', 'WAITING_AUTHORITY', 'RESOLVED', 'WAIVED');
CREATE TYPE ref.priority AS ENUM ('P0', 'P1', 'P2', 'P3');
CREATE TYPE ref.decision_step_type AS ENUM
  ('INPUT_VALIDATION', 'SCENARIO_SELECTION', 'CLASSIFICATION', 'RULE_SELECTION',
   'ELIGIBILITY', 'CALCULATION', 'RISK_ASSESSMENT', 'OUTPUT');
CREATE TYPE ref.risk_level AS ENUM ('NONE', 'LOW', 'MEDIUM', 'HIGH', 'BLOCKING');
CREATE TYPE ref.risk_tag_type AS ENUM
  ('GRI_2A', 'HEADING_8708_EXCLUSION', 'AP_REGULATORY');
CREATE TYPE ref.review_decision AS ENUM
  ('PENDING', 'APPROVED', 'REJECTED', 'NEEDS_MORE_EVIDENCE');

CREATE TABLE ref.country (
  country_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  iso2 char(2) NOT NULL UNIQUE,
  iso3 char(3) NOT NULL UNIQUE,
  country_name_en text NOT NULL,
  country_name_cn text,
  currency_code char(3),
  timezone_name text,
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ref.authority (
  authority_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  authority_code text NOT NULL UNIQUE,
  country_id uuid REFERENCES ref.country(country_id),
  authority_name text NOT NULL,
  official_url text,
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ref.trade_agreement (
  trade_agreement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agreement_code text NOT NULL,
  agreement_name text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  effective_from date NOT NULL,
  effective_to date,
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (agreement_code, version)
);

CREATE TABLE evidence.source_document (
  source_document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_code text NOT NULL UNIQUE,
  authority_id uuid REFERENCES ref.authority(authority_id),
  document_title text NOT NULL,
  document_number text,
  source_type ref.source_type NOT NULL,
  official_status ref.official_status NOT NULL DEFAULT 'UNKNOWN',
  canonical_url text,
  publication_date date,
  effective_from date,
  effective_to date,
  accessed_at timestamptz NOT NULL,
  language_code varchar(12),
  content_sha256 char(64),
  archived_object_key text,
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (effective_from IS NULL OR effective_to IS NULL OR effective_to > effective_from),
  CHECK (content_sha256 IS NULL OR content_sha256 ~ '^[0-9a-fA-F]{64}$')
);

CREATE TABLE evidence.source_clause (
  source_clause_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clause_code text NOT NULL UNIQUE,
  source_document_id uuid NOT NULL
    REFERENCES evidence.source_document(source_document_id),
  locator_type text NOT NULL,
  locator_value text NOT NULL,
  original_text text,
  translated_text_cn text,
  evidence_summary text,
  extraction_method text,
  extracted_at timestamptz,
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_document_id, locator_type, locator_value)
);

CREATE TABLE rules.country_rule_card (
  rule_card_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_code text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  rule_domain ref.rule_domain NOT NULL,
  rule_name_cn text NOT NULL,
  rule_content text NOT NULL,
  condition_expression jsonb NOT NULL,
  formula_expression jsonb,
  tariff_version text,
  authority_id uuid REFERENCES ref.authority(authority_id),
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  source_clause_id uuid NOT NULL
    REFERENCES evidence.source_clause(source_clause_id),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  verified_at timestamptz,
  verified_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(condition_expression) = 'object'),
  CHECK (formula_expression IS NULL OR jsonb_typeof(formula_expression) = 'object'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  CHECK ((verification_status IN ('VERIFIED', 'RULING_CONFIRMED')) = (verified_at IS NOT NULL)),
  UNIQUE (rule_code, version)
);

CREATE TABLE customs.customs_classification_unit (
  ccu_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ccu_code text NOT NULL,
  ccu_name_cn text NOT NULL,
  ccu_name_en text NOT NULL,
  parent_ccu_id uuid REFERENCES customs.customs_classification_unit(ccu_id),
  vehicle_system text NOT NULL,
  unit_level ref.ccu_unit_level NOT NULL,
  function_description text NOT NULL,
  material_spec text,
  technical_qualifiers jsonb NOT NULL DEFAULT '{}'::jsonb,
  assembly_state ref.assembly_state NOT NULL DEFAULT 'UNKNOWN',
  included_items jsonb NOT NULL DEFAULT '[]'::jsonb,
  excluded_items jsonb NOT NULL DEFAULT '[]'::jsonb,
  required_input_fields jsonb NOT NULL DEFAULT '[]'::jsonb,
  gri_2a_risk ref.risk_level NOT NULL DEFAULT 'NONE',
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(technical_qualifiers) = 'object'),
  CHECK (jsonb_typeof(included_items) = 'array'),
  CHECK (jsonb_typeof(excluded_items) = 'array'),
  CHECK (jsonb_typeof(required_input_fields) = 'array'),
  UNIQUE (ccu_code, version)
);

CREATE TABLE customs.ccu_candidate_hs (
  candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ccu_id uuid NOT NULL
    REFERENCES customs.customs_classification_unit(ccu_id),
  candidate_rank smallint NOT NULL CHECK (candidate_rank BETWEEN 1 AND 3),
  hs_nomenclature_version text NOT NULL,
  hs6_code char(6) NOT NULL CHECK (hs6_code ~ '^[0-9]{6}$'),
  candidate_basis text NOT NULL,
  exclusion_notes text,
  source_clause_id uuid REFERENCES evidence.source_clause(source_clause_id),
  verification_status ref.verification_status NOT NULL DEFAULT 'CANDIDATE',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ccu_id, candidate_rank, hs_nomenclature_version),
  UNIQUE (ccu_id, hs6_code, hs_nomenclature_version)
);

CREATE TABLE customs.ccu_risk_tag (
  ccu_risk_tag_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ccu_id uuid NOT NULL
    REFERENCES customs.customs_classification_unit(ccu_id),
  risk_tag_type ref.risk_tag_type NOT NULL,
  risk_level ref.risk_level NOT NULL,
  trigger_condition jsonb NOT NULL,
  risk_note text NOT NULL,
  source_clause_id uuid REFERENCES evidence.source_clause(source_clause_id),
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(trigger_condition) = 'object'),
  UNIQUE (ccu_id, risk_tag_type)
);

CREATE TABLE customs.tariff_mapping (
  mapping_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mapping_code text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  candidate_id uuid NOT NULL REFERENCES customs.ccu_candidate_hs(candidate_id),
  tariff_version text NOT NULL,
  national_tariff_code text NOT NULL,
  tariff_description text NOT NULL,
  origin_regime ref.origin_regime NOT NULL,
  trade_agreement_id uuid REFERENCES ref.trade_agreement(trade_agreement_id),
  duty_rate numeric(12,8),
  rate_type ref.rate_type NOT NULL,
  additional_measure jsonb NOT NULL DEFAULT '{}'::jsonb,
  eligibility_condition jsonb NOT NULL DEFAULT '{}'::jsonb,
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  source_clause_id uuid NOT NULL REFERENCES evidence.source_clause(source_clause_id),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (national_tariff_code ~ '^[0-9]{6,12}$'),
  CHECK (duty_rate IS NULL OR duty_rate >= 0),
  CHECK (rate_type <> 'UNKNOWN' OR duty_rate IS NULL),
  CHECK (rate_type <> 'ZERO' OR duty_rate = 0),
  CHECK (origin_regime <> 'FTA' OR trade_agreement_id IS NOT NULL),
  CHECK (jsonb_typeof(additional_measure) = 'object'),
  CHECK (jsonb_typeof(eligibility_condition) = 'object'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (mapping_code, version)
);

CREATE TABLE rules.approval_matrix (
  requirement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  requirement_code text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  requirement_type ref.requirement_type NOT NULL,
  applicable_object text NOT NULL,
  import_mode ref.import_mode,
  powertrain ref.powertrain,
  trigger_condition jsonb NOT NULL,
  required_document jsonb,
  authority_id uuid REFERENCES ref.authority(authority_id),
  benefit_rule_id uuid REFERENCES rules.country_rule_card(rule_card_id),
  failure_consequence text,
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  source_clause_id uuid NOT NULL REFERENCES evidence.source_clause(source_clause_id),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(trigger_condition) = 'object'),
  CHECK (required_document IS NULL OR jsonb_typeof(required_document) IN ('array', 'object')),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (requirement_code, version)
);

CREATE TABLE rules.tax_scenario_model (
  scenario_model_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_code text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  scenario_name_cn text NOT NULL,
  import_mode ref.import_mode NOT NULL,
  origin_regime ref.origin_regime NOT NULL,
  powertrain ref.powertrain,
  classification_route text NOT NULL,
  required_input_fields jsonb NOT NULL,
  calculation_dsl jsonb NOT NULL,
  fallback_scenario_id uuid
    REFERENCES rules.tax_scenario_model(scenario_model_id),
  output_scope jsonb NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(required_input_fields) = 'array'),
  CHECK (jsonb_typeof(calculation_dsl) = 'object'),
  CHECK (jsonb_typeof(output_scope) = 'object'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  CHECK (fallback_scenario_id IS NULL OR fallback_scenario_id <> scenario_model_id),
  UNIQUE (scenario_code, version)
);

CREATE TABLE rules.scenario_rule_link (
  scenario_rule_link_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_model_id uuid NOT NULL
    REFERENCES rules.tax_scenario_model(scenario_model_id),
  rule_card_id uuid NOT NULL REFERENCES rules.country_rule_card(rule_card_id),
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  mandatory boolean NOT NULL DEFAULT true,
  UNIQUE (scenario_model_id, rule_card_id),
  UNIQUE (scenario_model_id, sequence_no)
);

CREATE TABLE rules.scenario_requirement_link (
  scenario_requirement_link_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_model_id uuid NOT NULL
    REFERENCES rules.tax_scenario_model(scenario_model_id),
  requirement_id uuid NOT NULL REFERENCES rules.approval_matrix(requirement_id),
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  blocking boolean NOT NULL DEFAULT true,
  UNIQUE (scenario_model_id, requirement_id),
  UNIQUE (scenario_model_id, sequence_no)
);

CREATE TABLE enterprise.vehicle_model (
  vehicle_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  model_code text NOT NULL,
  vehicle_type text NOT NULL,
  powertrain ref.powertrain NOT NULL,
  technical_attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(technical_attributes) = 'object'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (model_code, version)
);

CREATE TABLE enterprise.enterprise_part (
  enterprise_part_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  enterprise_code text NOT NULL,
  part_no text NOT NULL,
  part_name_cn text,
  part_name_en text,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(attributes) = 'object'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (enterprise_code, part_no, version)
);

CREATE TABLE enterprise.enterprise_part_ccu_link (
  part_ccu_link_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  enterprise_part_id uuid NOT NULL
    REFERENCES enterprise.enterprise_part(enterprise_part_id),
  ccu_id uuid NOT NULL
    REFERENCES customs.customs_classification_unit(ccu_id),
  mapping_basis text NOT NULL,
  confidence numeric(5,4) CHECK (confidence BETWEEN 0 AND 1),
  effective_from date NOT NULL,
  effective_to date,
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (enterprise_part_id, ccu_id, effective_from)
);

CREATE TABLE enterprise.bom_version (
  bom_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id uuid NOT NULL REFERENCES enterprise.vehicle_model(vehicle_id),
  bom_code text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  effective_from date NOT NULL,
  effective_to date,
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (bom_code, version)
);

CREATE TABLE enterprise.bom_line (
  bom_line_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bom_version_id uuid NOT NULL REFERENCES enterprise.bom_version(bom_version_id),
  enterprise_part_id uuid NOT NULL
    REFERENCES enterprise.enterprise_part(enterprise_part_id),
  quantity_per_vehicle numeric(20,6) NOT NULL CHECK (quantity_per_vehicle > 0),
  unit_value numeric(20,6) CHECK (unit_value IS NULL OR unit_value >= 0),
  currency_code char(3),
  origin_country_id uuid REFERENCES ref.country(country_id),
  shipment_group text,
  included_flag boolean NOT NULL DEFAULT true,
  UNIQUE (bom_version_id, enterprise_part_id, shipment_group)
);

CREATE TABLE enterprise.scenario_input (
  scenario_input_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_code text NOT NULL UNIQUE,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  vehicle_id uuid REFERENCES enterprise.vehicle_model(vehicle_id),
  bom_version_id uuid REFERENCES enterprise.bom_version(bom_version_id),
  import_date date NOT NULL,
  import_mode ref.import_mode NOT NULL,
  origin_country_id uuid REFERENCES ref.country(country_id),
  input_payload jsonb NOT NULL,
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(input_payload) = 'object')
);

CREATE TABLE enterprise.input_snapshot (
  input_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_input_id uuid NOT NULL
    REFERENCES enterprise.scenario_input(scenario_input_id),
  payload jsonb NOT NULL,
  payload_sha256 char(64) NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(payload) = 'object'),
  CHECK (payload_sha256 ~ '^[0-9a-fA-F]{64}$')
);

CREATE TABLE calc.calculation_run (
  calculation_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_code text NOT NULL UNIQUE,
  scenario_model_id uuid NOT NULL
    REFERENCES rules.tax_scenario_model(scenario_model_id),
  input_snapshot_id uuid NOT NULL
    REFERENCES enterprise.input_snapshot(input_snapshot_id),
  rule_snapshot_at timestamptz NOT NULL,
  engine_version text NOT NULL,
  run_status ref.calculation_status NOT NULL DEFAULT 'QUEUED',
  completeness ref.completeness NOT NULL DEFAULT 'BLOCKED',
  currency_code char(3) NOT NULL,
  base_value numeric(20,6),
  gross_tax numeric(20,6),
  recoverable_tax numeric(20,6),
  net_tax numeric(20,6),
  effective_tax_rate numeric(12,8),
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  error_summary text,
  CHECK (base_value IS NULL OR base_value >= 0),
  CHECK (gross_tax IS NULL OR gross_tax >= 0),
  CHECK (recoverable_tax IS NULL OR recoverable_tax >= 0),
  CHECK (net_tax IS NULL OR net_tax >= 0),
  CHECK (completed_at IS NULL OR completed_at >= started_at)
);

CREATE TABLE calc.calculation_line (
  calculation_line_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  calculation_run_id uuid NOT NULL
    REFERENCES calc.calculation_run(calculation_run_id),
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  tax_code text NOT NULL,
  base_expression jsonb NOT NULL,
  base_amount numeric(20,6),
  rate_type ref.rate_type NOT NULL,
  rate numeric(12,8),
  tax_expression jsonb NOT NULL,
  gross_tax_amount numeric(20,6),
  recoverable_fraction numeric(12,8)
    CHECK (recoverable_fraction IS NULL OR recoverable_fraction BETWEEN 0 AND 1),
  net_tax_amount numeric(20,6),
  rule_card_id uuid REFERENCES rules.country_rule_card(rule_card_id),
  tariff_mapping_id uuid REFERENCES customs.tariff_mapping(mapping_id),
  line_status ref.calculation_status NOT NULL,
  notes text,
  CHECK (jsonb_typeof(base_expression) = 'object'),
  CHECK (jsonb_typeof(tax_expression) = 'object'),
  CHECK (rate IS NULL OR rate >= 0),
  UNIQUE (calculation_run_id, sequence_no)
);

CREATE TABLE audit.decision_trace (
  decision_trace_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  calculation_run_id uuid NOT NULL
    REFERENCES calc.calculation_run(calculation_run_id),
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  step_type ref.decision_step_type NOT NULL,
  decision_question text NOT NULL,
  input_record_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  rule_record_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_clause_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  explicit_rationale text NOT NULL,
  result jsonb NOT NULL,
  confidence numeric(5,4) CHECK (confidence BETWEEN 0 AND 1),
  human_review_required boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(input_record_refs) = 'array'),
  CHECK (jsonb_typeof(rule_record_refs) = 'array'),
  CHECK (jsonb_typeof(source_clause_refs) = 'array'),
  CHECK (jsonb_typeof(result) IN ('object', 'array')),
  UNIQUE (calculation_run_id, sequence_no)
);

COMMENT ON TABLE audit.decision_trace IS
  'Stores auditable business decisions and explicit reasons; never hidden model chain-of-thought.';

CREATE TABLE audit.missing_data (
  missing_data_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  calculation_run_id uuid REFERENCES calc.calculation_run(calculation_run_id),
  field_path text NOT NULL,
  description text NOT NULL,
  data_owner text,
  data_kind ref.missing_data_kind NOT NULL,
  data_ownership ref.data_ownership NOT NULL,
  blocking_scope text NOT NULL,
  priority ref.priority NOT NULL,
  next_action text NOT NULL,
  official_entry_url text,
  status ref.missing_data_status NOT NULL DEFAULT 'OPEN',
  resolved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((status = 'RESOLVED') = (resolved_at IS NOT NULL))
);

CREATE TABLE audit.review_record (
  review_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type text NOT NULL,
  entity_id uuid NOT NULL,
  decision ref.review_decision NOT NULL DEFAULT 'PENDING',
  reviewer text NOT NULL,
  review_notes text,
  reviewed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ai.llm_view_item (
  llm_view_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  calculation_run_id uuid NOT NULL
    REFERENCES calc.calculation_run(calculation_run_id),
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  record_type text NOT NULL,
  record_id uuid NOT NULL,
  field_subset jsonb NOT NULL,
  why_read text NOT NULL,
  source_clause_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  data_quality ref.verification_status NOT NULL,
  prompt_safe boolean NOT NULL DEFAULT false,
  CHECK (jsonb_typeof(field_subset) = 'object'),
  CHECK (jsonb_typeof(source_clause_refs) = 'array'),
  UNIQUE (calculation_run_id, sequence_no)
);

CREATE INDEX idx_source_document_authority
  ON evidence.source_document(authority_id);
CREATE INDEX idx_source_clause_document
  ON evidence.source_clause(source_document_id);
CREATE INDEX idx_country_rule_effective
  ON rules.country_rule_card(country_id, rule_domain, effective_from, effective_to);
CREATE INDEX idx_ccu_parent
  ON customs.customs_classification_unit(parent_ccu_id);
CREATE INDEX idx_candidate_hs6
  ON customs.ccu_candidate_hs(hs6_code, hs_nomenclature_version);
CREATE INDEX idx_ccu_risk_tag
  ON customs.ccu_risk_tag(risk_tag_type, risk_level);
CREATE INDEX idx_tariff_mapping_lookup
  ON customs.tariff_mapping
    (country_id, national_tariff_code, origin_regime, effective_from, effective_to);
CREATE INDEX idx_approval_lookup
  ON rules.approval_matrix(country_id, import_mode, powertrain, effective_from, effective_to);
CREATE INDEX idx_part_ccu_link_part
  ON enterprise.enterprise_part_ccu_link(enterprise_part_id, effective_from, effective_to);
CREATE INDEX idx_calc_run_scenario
  ON calc.calculation_run(scenario_model_id, started_at);
CREATE INDEX idx_missing_data_open
  ON audit.missing_data(priority, status)
  WHERE status NOT IN ('RESOLVED', 'WAIVED');

COMMIT;
