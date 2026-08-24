BEGIN;

ALTER TABLE enterprise.scenario_input
  ADD COLUMN IF NOT EXISTS decision_project_id uuid
    REFERENCES enterprise.decision_project(project_id);

CREATE INDEX IF NOT EXISTS idx_scenario_input_decision_project
  ON enterprise.scenario_input(decision_project_id, created_at DESC);

ALTER TABLE calc.calculation_line
  ADD COLUMN IF NOT EXISTS vehicle_tariff_rate_line_id uuid
    REFERENCES customs.vehicle_tariff_rate_line(vehicle_tariff_rate_line_id);

CREATE INDEX IF NOT EXISTS idx_calculation_line_vehicle_tariff
  ON calc.calculation_line(vehicle_tariff_rate_line_id);

COMMIT;
