BEGIN;

CREATE TABLE IF NOT EXISTS enterprise.decision_project (
  project_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_code text NOT NULL UNIQUE,
  enterprise_code text NOT NULL,
  project_name text NOT NULL,
  country_id uuid NOT NULL REFERENCES ref.country(country_id),
  vehicle_id uuid REFERENCES enterprise.vehicle_model(vehicle_id),
  calculation_date date NOT NULL DEFAULT current_date,
  selected_route_code text,
  route_facts jsonb NOT NULL DEFAULT '{}'::jsonb,
  project_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  record_status ref.record_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(route_facts) = 'object'),
  CHECK (jsonb_typeof(project_payload) = 'object')
);

CREATE TABLE IF NOT EXISTS enterprise.project_input_value (
  project_input_value_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL
    REFERENCES enterprise.decision_project(project_id) ON DELETE CASCADE,
  field_path text NOT NULL,
  value_payload jsonb,
  value_status ref.input_value_status NOT NULL DEFAULT 'EMPTY',
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  notes text,
  provided_by text,
  provided_at timestamptz,
  verified_by text,
  verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(evidence_refs) = 'array'),
  CHECK (
    (value_status = 'EMPTY' AND value_payload IS NULL)
    OR (value_status <> 'EMPTY' AND value_payload IS NOT NULL)
  ),
  UNIQUE (project_id, field_path)
);

CREATE TABLE IF NOT EXISTS enterprise.project_approval (
  project_approval_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL
    REFERENCES enterprise.decision_project(project_id) ON DELETE CASCADE,
  requirement_id uuid NOT NULL REFERENCES rules.approval_matrix(requirement_id),
  approval_reference text,
  approval_status text NOT NULL DEFAULT 'NOT_PROVIDED',
  authority_name text,
  issue_date date,
  effective_from date,
  effective_to date,
  covered_model text,
  covered_tariff_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  approved_rate numeric(18,8),
  exemption_scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  evidence_ref text,
  notes text,
  verification_status ref.verification_status NOT NULL DEFAULT 'UNVERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    approval_status IN (
      'NOT_PROVIDED', 'PROVIDED', 'VERIFIED', 'REJECTED', 'EXPIRED'
    )
  ),
  CHECK (jsonb_typeof(covered_tariff_codes) = 'array'),
  CHECK (jsonb_typeof(exemption_scope) = 'object'),
  CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from),
  UNIQUE (project_id, requirement_id)
);

CREATE TABLE IF NOT EXISTS enterprise.project_tariff_selection (
  project_tariff_selection_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL
    REFERENCES enterprise.decision_project(project_id) ON DELETE CASCADE,
  selection_scope text NOT NULL,
  tariff_mapping_id uuid REFERENCES customs.tariff_mapping(mapping_id),
  vehicle_tariff_rate_line_id uuid
    REFERENCES customs.vehicle_tariff_rate_line(vehicle_tariff_rate_line_id),
  selected_by text NOT NULL,
  selection_note text,
  verification_status ref.verification_status NOT NULL DEFAULT 'CANDIDATE',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    num_nonnulls(tariff_mapping_id, vehicle_tariff_rate_line_id) = 1
  ),
  UNIQUE (project_id, selection_scope)
);

CREATE INDEX IF NOT EXISTS idx_decision_project_country
  ON enterprise.decision_project(country_id, calculation_date, record_status);

CREATE INDEX IF NOT EXISTS idx_project_input_project
  ON enterprise.project_input_value(project_id, field_path);

CREATE INDEX IF NOT EXISTS idx_project_approval_project
  ON enterprise.project_approval(project_id, approval_status);

CREATE OR REPLACE VIEW enterprise.v_project_input_completion AS
WITH required_fields AS (
  SELECT
    project.project_id,
    route.route_code,
    required.field_path
  FROM enterprise.decision_project project
  JOIN rules.vehicle_tax_route route
    ON route.route_code = project.selected_route_code
   AND route.country_id = project.country_id
   AND route.record_status = 'ACTIVE'
   AND route.effective_from <= project.calculation_date
   AND (
     route.effective_to IS NULL
     OR route.effective_to > project.calculation_date
   )
  CROSS JOIN LATERAL jsonb_array_elements_text(
    route.required_input_fields
  ) required(field_path)
  WHERE project.record_status IN ('DRAFT', 'ACTIVE')
)
SELECT
  project.project_id,
  project.project_code,
  project.selected_route_code,
  count(required.field_path) AS required_count,
  count(required.field_path) FILTER (
    WHERE value.value_status IN ('PROVIDED', 'VERIFIED')
      AND value.value_payload IS NOT NULL
      AND lower(trim(value.value_payload #>> '{}')) NOT IN (
        '', 'unknown', 'pending', '待确认'
      )
  ) AS accepted_required_count,
  count(required.field_path) FILTER (
    WHERE value.project_input_value_id IS NULL
       OR value.value_status NOT IN ('PROVIDED', 'VERIFIED')
       OR value.value_payload IS NULL
       OR lower(trim(value.value_payload #>> '{}')) IN (
         '', 'unknown', 'pending', '待确认'
       )
  ) AS missing_required_count,
  CASE
    WHEN count(required.field_path) = 0 THEN 0::numeric
    ELSE round(
      count(required.field_path) FILTER (
        WHERE value.value_status IN ('PROVIDED', 'VERIFIED')
          AND value.value_payload IS NOT NULL
          AND lower(trim(value.value_payload #>> '{}')) NOT IN (
            '', 'unknown', 'pending', '待确认'
          )
      )::numeric / count(required.field_path),
      4
    )
  END AS completion_ratio,
  count(required.field_path) > 0
    AND count(required.field_path) FILTER (
      WHERE value.project_input_value_id IS NULL
         OR value.value_status NOT IN ('PROVIDED', 'VERIFIED')
         OR value.value_payload IS NULL
         OR lower(trim(value.value_payload #>> '{}')) IN (
           '', 'unknown', 'pending', '待确认'
         )
    ) = 0 AS ready_for_preview
FROM enterprise.decision_project project
LEFT JOIN required_fields required ON required.project_id = project.project_id
LEFT JOIN enterprise.project_input_value value
  ON value.project_id = project.project_id
 AND value.field_path = required.field_path
GROUP BY project.project_id;

COMMIT;
