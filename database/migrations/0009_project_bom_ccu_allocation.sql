BEGIN;

CREATE TABLE IF NOT EXISTS enterprise.project_bom_line (
  project_bom_line_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL
    REFERENCES enterprise.decision_project(project_id) ON DELETE CASCADE,
  line_no integer NOT NULL CHECK (line_no > 0),
  enterprise_part_no text NOT NULL,
  part_name text,
  ccu_id uuid NOT NULL
    REFERENCES customs.customs_classification_unit(ccu_id),
  kd_tax_bucket_id uuid
    REFERENCES rules.kd_tax_bucket_definition(kd_tax_bucket_id),
  customs_value numeric(20,6) NOT NULL CHECK (customs_value >= 0),
  quantity numeric(20,6) NOT NULL DEFAULT 1 CHECK (quantity > 0),
  currency_code char(3) NOT NULL DEFAULT 'MYR',
  origin_country_id uuid REFERENCES ref.country(country_id),
  local_or_imported text NOT NULL DEFAULT 'IMPORTED'
    CHECK (local_or_imported IN ('IMPORTED', 'LOCAL')),
  enterprise_inputs_complete boolean NOT NULL DEFAULT false,
  gri_2a_review_complete boolean NOT NULL DEFAULT false,
  notes text,
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, line_no),
  UNIQUE (project_id, ccu_id)
);

CREATE TABLE IF NOT EXISTS enterprise.project_bom_tariff_selection (
  project_bom_tariff_selection_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_bom_line_id uuid NOT NULL
    REFERENCES enterprise.project_bom_line(project_bom_line_id) ON DELETE CASCADE,
  regime text NOT NULL CHECK (regime IN ('MFN', 'ACFTA', 'RCEP')),
  tariff_mapping_id uuid NOT NULL
    REFERENCES customs.tariff_mapping(mapping_id),
  selected_by text NOT NULL,
  selection_note text,
  verification_status ref.verification_status NOT NULL DEFAULT 'CANDIDATE',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_bom_line_id, regime)
);

CREATE INDEX IF NOT EXISTS idx_project_bom_project
  ON enterprise.project_bom_line(project_id, line_no);

CREATE INDEX IF NOT EXISTS idx_project_bom_ccu
  ON enterprise.project_bom_line(ccu_id);

CREATE INDEX IF NOT EXISTS idx_project_bom_selection_line
  ON enterprise.project_bom_tariff_selection(project_bom_line_id, regime);

COMMIT;
