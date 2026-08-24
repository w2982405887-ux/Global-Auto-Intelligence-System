BEGIN;

-- Resolve the four PDK 2025 parent-indentation gaps retained by seed 0007.
-- Authoritative source: Customs Duties Order 2025, P.U. (A) 384/2025.
-- PDF pages: 1074-1075, 1248-1250 and 1251-1252.

UPDATE evidence.source_document
SET content_sha256 =
      'e51c740cf95290cb71cd473596adc21ef159d1aa4f2a0282c73b4b3815beea99',
    archived_object_key =
      'evidence/my/2026-07-28/PUA_384_2025.pdf',
    accessed_at = TIMESTAMPTZ '2026-07-28 17:30:00+08',
    official_status = 'OFFICIAL',
    record_status = 'ACTIVE'
WHERE source_code = 'SRC-MY-PDK-2025';

WITH clause_rows (
  clause_code, locator_value, original_text,
  translated_text_cn, evidence_summary
) AS (
  VALUES
    ('CLAUSE-MY-PDK2025-850152-PARENT-INDENTATION',
     'First Schedule, PDF pages 1074-1075, heading 8501.52',
     '8501.52: output exceeding 750 W but not exceeding 75 kW. 8501.52.12 00 is under output not exceeding 1 kW; 8501.52.22 00 is under output exceeding 1 kW but not exceeding 37.5 kW; 8501.52.32 00 is under output exceeding 37.5 kW but not exceeding 75 kW. Each is of a kind used for vehicles in Chapter 87.',
     '8501.52项下车辆用三组分别为：8501521200，输出功率超过750 W但不超过1 kW；8501522200，超过1 kW但不超过37.5 kW；8501523200，超过37.5 kW但不超过75 kW。',
     'The official schedule resolves the three omitted motor-output parent bands.'),
    ('CLAUSE-MY-PDK2025-870870-PARENT-INDENTATION',
     'First Schedule, PDF pages 1248-1249, heading 8708.70',
     '8708.70 parent groups are Hub-caps; Wheels fitted with tyres; Wheels not fitted with tyres; and Other. For vehicles of heading 87.03 the respective national lines are 8708.70.16 00, 8708.70.22 00, 8708.70.32 00 and 8708.70.97 00.',
     '8708.70父级依次为轮毂罩、装有轮胎的车轮、未装轮胎的车轮和其他；8703品目车辆对应完整税号分别为8708701600、8708702200、8708703200和8708709700。',
     'A complete road wheel maps conditionally to 8708702200 when fitted with a tyre or 8708703200 when not fitted. Hub-cap and residual parts lines are outside the defined road-wheel CCU.'),
    ('CLAUSE-MY-PDK2025-870880-PARENT-INDENTATION',
     'First Schedule, PDF pages 1249-1250, heading 8708.80',
     '8708.80 parent groups are Suspension systems and Parts. For vehicles of heading 87.03 the national lines are 8708.80.16 00 for suspension systems and 8708.80.92 00 for parts.',
     '8708.80父级分为悬架系统和零件；8703品目车辆分别对应8708801600和8708809200。',
     'The shock-absorber or strut CCU is a suspension part and therefore maps conditionally to 8708809200; a complete suspension system requires a different CCU/presentation assessment.'),
    ('CLAUSE-MY-PDK2025-870894-PARENT-INDENTATION',
     'First Schedule, PDF pages 1251-1252, heading 8708.94',
     '8708.94 parent groups are Steering wheels with airbag assemblies and Other. Under Other, 8708.94.95 00 is for vehicles of heading 87.03.',
     '8708.94父级分为带安全气囊总成的方向盘和其他；其他项下用于8703品目车辆的完整税号为8708949500。',
     'The steering gear or steering column CCU excludes steering wheels and maps conditionally to the Other branch, 8708949500.')
)
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary,
  extraction_method, extracted_at, verification_status
)
SELECT
  c.clause_code,
  (SELECT source_document_id
   FROM evidence.source_document
   WHERE source_code = 'SRC-MY-PDK-2025'),
  'PDF_PAGE', c.locator_value, c.original_text,
  c.translated_text_cn, c.evidence_summary,
  'PDF_TEXT_EXTRACTION_AND_VISUAL_PAGE_REVIEW',
  TIMESTAMPTZ '2026-07-28 17:30:00+08', 'VERIFIED'
FROM clause_rows c
ON CONFLICT (clause_code) DO UPDATE
SET source_document_id = EXCLUDED.source_document_id,
    locator_type = EXCLUDED.locator_type,
    locator_value = EXCLUDED.locator_value,
    original_text = EXCLUDED.original_text,
    translated_text_cn = EXCLUDED.translated_text_cn,
    evidence_summary = EXCLUDED.evidence_summary,
    extraction_method = EXCLUDED.extraction_method,
    extracted_at = EXCLUDED.extracted_at,
    verification_status = 'VERIFIED';

-- ---------------------------------------------------------------------------
-- Electric traction motor: the official output bands resolve 12/22/32.
-- ---------------------------------------------------------------------------

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Output exceeding 750 W but not exceeding 1 kW; of a kind used for vehicles in Chapter 87',
    eligibility_condition =
      '{"all":[{"field":"part.current_type","operator":"EQ","value":"MULTI_PHASE_AC"},{"field":"part.rated_output_kw","operator":"GT","value":0.75},{"field":"part.rated_output_kw","operator":"LTE","value":1},{"field":"vehicle.chapter","operator":"EQ","value":"87"}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Output exceeding 750 W but not exceeding 1 kW","classification_disposition":"CONDITIONALLY_CONFIRMED"}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-850152-PARENT-INDENTATION'
    ),
    record_status = 'ACTIVE',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code = 'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501521200-R1';

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Output exceeding 1 kW but not exceeding 37.5 kW; of a kind used for vehicles in Chapter 87',
    eligibility_condition =
      '{"all":[{"field":"part.current_type","operator":"EQ","value":"MULTI_PHASE_AC"},{"field":"part.rated_output_kw","operator":"GT","value":1},{"field":"part.rated_output_kw","operator":"LTE","value":37.5},{"field":"vehicle.chapter","operator":"EQ","value":"87"}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Output exceeding 1 kW but not exceeding 37.5 kW","classification_disposition":"CONDITIONALLY_CONFIRMED"}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-850152-PARENT-INDENTATION'
    ),
    record_status = 'ACTIVE',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code = 'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501522200-R1';

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Output exceeding 37.5 kW but not exceeding 75 kW; of a kind used for vehicles in Chapter 87',
    eligibility_condition =
      '{"all":[{"field":"part.current_type","operator":"EQ","value":"MULTI_PHASE_AC"},{"field":"part.rated_output_kw","operator":"GT","value":37.5},{"field":"part.rated_output_kw","operator":"LTE","value":75},{"field":"vehicle.chapter","operator":"EQ","value":"87"}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Output exceeding 37.5 kW but not exceeding 75 kW","classification_disposition":"CONDITIONALLY_CONFIRMED"}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-850152-PARENT-INDENTATION'
    ),
    record_status = 'ACTIVE',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code = 'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501523200-R1';

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Output exceeding 75 kW; of a kind used for vehicles in Chapter 87',
    eligibility_condition =
      '{"all":[{"field":"part.current_type","operator":"EQ","value":"MULTI_PHASE_AC"},{"field":"part.rated_output_kw","operator":"GT","value":75},{"field":"vehicle.chapter","operator":"EQ","value":"87"}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Output exceeding 75 kW","classification_disposition":"CONDITIONALLY_CONFIRMED"}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-850152-PARENT-INDENTATION'
    ),
    record_status = 'ACTIVE',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code = 'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501531000-R1';

-- ---------------------------------------------------------------------------
-- Road wheel: keep fitted/unfitted wheel routes; reject hub-cap/residual part.
-- ---------------------------------------------------------------------------

UPDATE customs.tariff_mapping tm
SET tariff_description = 'Hub-caps - for vehicles of heading 87.03',
    eligibility_condition =
      '{"all":[{"field":"part.component_form","operator":"EQ","value":"HUB_CAP"},{"field":"classification.ccu_reassignment_required","operator":"EQ","value":true}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Hub-caps","classification_disposition":"EXCLUDED_FROM_ROAD_WHEEL_CCU","reason":"The CCU excludes decorative covers and hub-caps."}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-870870-PARENT-INDENTATION'
    ),
    record_status = 'REJECTED',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code = 'MAP-MY-MFN-CCU-ROAD-WHEEL-8708701600-R1';

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Wheels fitted with tyres - for vehicles of heading 87.03',
    eligibility_condition =
      '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"part.component_form","operator":"EQ","value":"COMPLETE_WHEEL"},{"field":"part.with_tyre","operator":"EQ","value":true}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Wheels fitted with tyres","classification_disposition":"CONDITIONALLY_CONFIRMED"}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-870870-PARENT-INDENTATION'
    ),
    record_status = 'ACTIVE',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code = 'MAP-MY-MFN-CCU-ROAD-WHEEL-8708702200-R1';

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Wheels not fitted with tyres - for vehicles of heading 87.03',
    eligibility_condition =
      '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"part.component_form","operator":"EQ","value":"COMPLETE_WHEEL"},{"field":"part.with_tyre","operator":"EQ","value":false}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Wheels not fitted with tyres","classification_disposition":"CONDITIONALLY_CONFIRMED"}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-870870-PARENT-INDENTATION'
    ),
    record_status = 'ACTIVE',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code = 'MAP-MY-MFN-CCU-ROAD-WHEEL-8708703200-R1';

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Other road-wheel parts and accessories - for vehicles of heading 87.03',
    eligibility_condition =
      '{"all":[{"field":"part.component_form","operator":"EQ","value":"OTHER_WHEEL_PART_OR_ACCESSORY"},{"field":"classification.ccu_reassignment_required","operator":"EQ","value":true}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Other","classification_disposition":"EXCLUDED_FROM_COMPLETE_ROAD_WHEEL_CCU","reason":"The defined CCU is a complete road wheel, not a residual wheel part or accessory."}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-870870-PARENT-INDENTATION'
    ),
    record_status = 'REJECTED',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code = 'MAP-MY-MFN-CCU-ROAD-WHEEL-8708709700-R1';

-- ---------------------------------------------------------------------------
-- Shock absorber / strut: part route confirmed; system route rejected for CCU.
-- ---------------------------------------------------------------------------

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Suspension systems - for vehicles of heading 87.03',
    eligibility_condition =
      '{"all":[{"field":"part.presentation_scope","operator":"EQ","value":"COMPLETE_SUSPENSION_SYSTEM"},{"field":"classification.ccu_reassignment_required","operator":"EQ","value":true}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Suspension systems","classification_disposition":"EXCLUDED_FROM_SHOCK_ABSORBER_STRUT_CCU","reason":"A complete suspension system is broader than the defined shock-absorber/strut CCU."}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-870880-PARENT-INDENTATION'
    ),
    record_status = 'REJECTED',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code =
      'MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708801600-R1';

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Suspension parts - for vehicles of heading 87.03',
    eligibility_condition =
      '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"part.presentation_scope","operator":"IN","value":["SHOCK_ABSORBER","STRUT","SUSPENSION_PART"]}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Parts","classification_disposition":"CONDITIONALLY_CONFIRMED"}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-870880-PARENT-INDENTATION'
    ),
    record_status = 'ACTIVE',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code =
      'MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708809200-R1';

-- ---------------------------------------------------------------------------
-- Steering gear / column: "Other" branch confirmed; airbag steering wheel
-- remains outside the CCU definition.
-- ---------------------------------------------------------------------------

UPDATE customs.tariff_mapping tm
SET tariff_description =
      'Other than steering wheels with airbag assemblies - for vehicles of heading 87.03',
    eligibility_condition =
      '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"part.component_type","operator":"IN","value":["STEERING_GEAR","STEERING_RACK","STEERING_COLUMN"]},{"field":"part.steering_wheel_with_airbag","operator":"EQ","value":false},{"field":"classification.separate_motor_or_ecu_reviewed","operator":"EQ","value":true}]}'::jsonb,
    additional_measure = tm.additional_measure ||
      '{"pdk_parent_group":"Other","classification_disposition":"CONDITIONALLY_CONFIRMED","excluded_parent_group":"Steering wheels with airbag assemblies"}'::jsonb,
    source_clause_id = (
      SELECT source_clause_id FROM evidence.source_clause
      WHERE clause_code = 'CLAUSE-MY-PDK2025-870894-PARENT-INDENTATION'
    ),
    record_status = 'ACTIVE',
    verification_status = 'VERIFIED',
    updated_at = now()
WHERE tm.mapping_code =
      'MAP-MY-MFN-CCU-STEERING-GEAR-COLUMN-8708949500-R1';

-- Promote the generic HS6 route only to the extent of the verified,
-- condition-based mapping above. This is not an enterprise-item decision.
UPDATE customs.ccu_candidate_hs h
SET source_clause_id = CASE h.hs6_code
      WHEN '850152' THEN (
        SELECT source_clause_id FROM evidence.source_clause
        WHERE clause_code = 'CLAUSE-MY-PDK2025-850152-PARENT-INDENTATION')
      WHEN '850153' THEN (
        SELECT source_clause_id FROM evidence.source_clause
        WHERE clause_code = 'CLAUSE-MY-PDK2025-850152-PARENT-INDENTATION')
      WHEN '870870' THEN (
        SELECT source_clause_id FROM evidence.source_clause
        WHERE clause_code = 'CLAUSE-MY-PDK2025-870870-PARENT-INDENTATION')
      WHEN '870880' THEN (
        SELECT source_clause_id FROM evidence.source_clause
        WHERE clause_code = 'CLAUSE-MY-PDK2025-870880-PARENT-INDENTATION')
      WHEN '870894' THEN (
        SELECT source_clause_id FROM evidence.source_clause
        WHERE clause_code = 'CLAUSE-MY-PDK2025-870894-PARENT-INDENTATION')
    END,
    verification_status = 'VERIFIED'
WHERE h.hs6_code IN ('850152','850153','870870','870880','870894')
  AND h.candidate_id IN (
    '65000000-0000-4000-8000-000000000021',
    '65000000-0000-4000-8000-000000000022',
    '65000000-0000-4000-8000-000000000071',
    '65000000-0000-4000-8000-000000000091',
    '65000000-0000-4000-8000-000000000101'
  );

-- The four public-research gaps are now resolved by the official PDF.
UPDATE audit.missing_data
SET status = 'RESOLVED',
    resolved_at = TIMESTAMPTZ '2026-07-28 17:30:00+08',
    description = description ||
      ' Resolved from the official P.U. (A) 384/2025 First Schedule PDF.'
WHERE field_path IN (
  'customs.pdk2025.omitted_parent_indentation[850152]',
  'customs.pdk2025.omitted_parent_indentation[870870]',
  'customs.pdk2025.omitted_parent_indentation[870880]',
  'customs.pdk2025.omitted_parent_indentation[870894]'
);

-- Keep enterprise gaps open, but replace the former parent-indentation
-- uncertainty with the now-executable technical selection rule.
UPDATE audit.missing_data
SET description =
      'Final motor line requires current type, continuous rated output in kW, integrated gearbox/inverter state and intended vehicle chapter. The PDK output bands are now verified.',
    next_action =
      'Enterprise to provide datasheet/nameplate and assembly drawing; apply 8501521200 for >0.75 to 1 kW, 8501522200 for >1 to 37.5 kW, 8501523200 for >37.5 to 75 kW, or 8501531000 for >75 kW when the other conditions are met.'
WHERE field_path =
  'enterprise.classification_input[CCU-TRACTION-MOTOR].motor_technology_and_rated_output';

UPDATE audit.missing_data
SET description =
      'A complete road wheel for heading 8703 maps to 8708702200 when fitted with a tyre or 8708703200 when not fitted. Enterprise presentation facts remain required.',
    next_action =
      'Enterprise to provide wheel drawing, material and tyre/hub presentation. Reassign hub-caps or residual wheel parts to a different CCU.'
WHERE field_path =
  'enterprise.classification_input[CCU-ROAD-WHEEL].wheel_form_and_national_branch';

UPDATE audit.missing_data
SET description =
      'A shock absorber or strut for heading 8703 maps conditionally to the suspension-parts line 8708809200. A complete suspension system is outside this CCU.',
    next_action =
      'Enterprise to provide drawing, presentation scope, spring/knuckle content and electronic-control details; reassign complete suspension systems to a broader CCU.'
WHERE field_path =
  'enterprise.classification_input[CCU-SHOCK-ABSORBER-STRUT].damper_configuration_and_national_branch';

UPDATE audit.missing_data
SET description =
      'A steering gear, rack or column for heading 8703 maps conditionally to the Other branch 8708949500; steering wheels with airbag assemblies are excluded.',
    next_action =
      'Enterprise to provide exact component type, assist type and integrated motor/ECU details, and confirm the item is not a steering wheel with airbag assembly.'
WHERE field_path =
  'enterprise.classification_input[CCU-STEERING-GEAR-COLUMN].steering_component_and_integrated_electrics';

COMMIT;

