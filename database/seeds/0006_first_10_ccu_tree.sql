BEGIN;

-- Four-level generic KD classification tree.
-- Hierarchy nodes organize the domain; only CUSTOMS_CLASSIFICATION_UNIT
-- records are tariff-research units.

INSERT INTO customs.customs_classification_unit (
  ccu_id, ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id,
  vehicle_system, unit_level, function_description, material_spec,
  technical_qualifiers, assembly_state, included_items, excluded_items,
  required_input_fields, gri_2a_risk, version, record_status,
  verification_status
) VALUES
  ('61000000-0000-4000-8000-000000000001','SYS-ELECTRIFIED-POWERTRAIN',
   '电动化动力系统','Electrified powertrain system',NULL,
   'ELECTRIFIED_POWERTRAIN','VEHICLE_SYSTEM',
   'Stores, converts and delivers electrical energy for vehicle propulsion.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('61000000-0000-4000-8000-000000000002','SYS-BODY',
   '车身系统','Body system',NULL,'BODY','VEHICLE_SYSTEM',
   'Provides the primary structural body and occupant enclosure.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('61000000-0000-4000-8000-000000000003','SYS-CHASSIS',
   '底盘系统','Chassis system',NULL,'CHASSIS','VEHICLE_SYSTEM',
   'Supports wheel, brake, steering and suspension functions.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),

  ('62000000-0000-4000-8000-000000000001','ASM-HV-ENERGY-STORAGE',
   '高压储能总成','High-voltage energy storage assembly',
   '61000000-0000-4000-8000-000000000001','HIGH_VOLTAGE_BATTERY','ASSEMBLY',
   'Stores traction electrical energy.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('62000000-0000-4000-8000-000000000002','ASM-ELECTRIC-DRIVE',
   '电驱动总成','Electric drive assembly',
   '61000000-0000-4000-8000-000000000001','ELECTRIC_DRIVE','ASSEMBLY',
   'Converts electrical energy into propulsion torque.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'HIGH',1,'ACTIVE','CANDIDATE'),
  ('62000000-0000-4000-8000-000000000003','ASM-POWER-ELECTRONICS',
   '功率电子总成','Power electronics assembly',
   '61000000-0000-4000-8000-000000000001','POWER_ELECTRONICS','ASSEMBLY',
   'Converts and controls traction and charging electrical power.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'HIGH',1,'ACTIVE','CANDIDATE'),
  ('62000000-0000-4000-8000-000000000004','ASM-BODY-IN-WHITE',
   '白车身总成','Body-in-white assembly',
   '61000000-0000-4000-8000-000000000002','BODY','ASSEMBLY',
   'Forms the structural vehicle body before trim and closures.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'HIGH',1,'ACTIVE','CANDIDATE'),
  ('62000000-0000-4000-8000-000000000005','ASM-ROAD-WHEEL',
   '车轮总成','Road wheel assembly',
   '61000000-0000-4000-8000-000000000003','WHEEL_AND_TYRE','ASSEMBLY',
   'Supports the tyre and transfers vehicle loads to the road.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('62000000-0000-4000-8000-000000000006','ASM-BRAKE',
   '制动总成','Brake assembly',
   '61000000-0000-4000-8000-000000000003','BRAKING','ASSEMBLY',
   'Generates and controls braking force.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('62000000-0000-4000-8000-000000000007','ASM-STEERING',
   '转向总成','Steering assembly',
   '61000000-0000-4000-8000-000000000003','STEERING','ASSEMBLY',
   'Transmits driver or actuator commands to road wheels.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('62000000-0000-4000-8000-000000000008','ASM-SUSPENSION',
   '悬架总成','Suspension assembly',
   '61000000-0000-4000-8000-000000000003','SUSPENSION','ASSEMBLY',
   'Supports the sprung mass and controls wheel motion.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),

  ('63000000-0000-4000-8000-000000000001','SUBASM-TRACTION-BATTERY-PACK',
   '动力电池包分总成','Traction battery pack subassembly',
   '62000000-0000-4000-8000-000000000001','HIGH_VOLTAGE_BATTERY','SUBASSEMBLY',
   'Combines cells or modules, enclosure and electrical management components.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('63000000-0000-4000-8000-000000000002','SUBASM-TRACTION-MOTOR',
   '驱动电机分总成','Traction motor subassembly',
   '62000000-0000-4000-8000-000000000002','ELECTRIC_DRIVE','SUBASSEMBLY',
   'Contains the propulsion electric motor, excluding an integrated gearbox unless specified.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'HIGH',1,'ACTIVE','CANDIDATE'),
  ('63000000-0000-4000-8000-000000000003','SUBASM-TRACTION-INVERTER',
   '驱动逆变器分总成','Traction inverter subassembly',
   '62000000-0000-4000-8000-000000000003','POWER_ELECTRONICS','SUBASSEMBLY',
   'Converts traction-battery direct current into controlled motor current.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'HIGH',1,'ACTIVE','CANDIDATE'),
  ('63000000-0000-4000-8000-000000000004','SUBASM-ONBOARD-CHARGER',
   '车载充电机分总成','On-board charger subassembly',
   '62000000-0000-4000-8000-000000000003','POWER_ELECTRONICS','SUBASSEMBLY',
   'Converts external AC supply into controlled DC charging power.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'HIGH',1,'ACTIVE','CANDIDATE'),
  ('63000000-0000-4000-8000-000000000005','SUBASM-DC-DC-CONVERTER',
   '直流变换器分总成','DC-DC converter subassembly',
   '62000000-0000-4000-8000-000000000003','POWER_ELECTRONICS','SUBASSEMBLY',
   'Converts DC voltage levels within the vehicle electrical architecture.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'HIGH',1,'ACTIVE','CANDIDATE'),
  ('63000000-0000-4000-8000-000000000006','SUBASM-PASSENGER-BODY-SHELL',
   '乘用车车身壳体分总成','Passenger-car body shell subassembly',
   '62000000-0000-4000-8000-000000000004','BODY','SUBASSEMBLY',
   'Structural passenger-car body shell, with or without closures as specified.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'HIGH',1,'ACTIVE','CANDIDATE'),
  ('63000000-0000-4000-8000-000000000007','SUBASM-ROAD-WHEEL',
   '道路车轮分总成','Road wheel subassembly',
   '62000000-0000-4000-8000-000000000005','WHEEL_AND_TYRE','SUBASSEMBLY',
   'Metal wheel, excluding tyre unless presented together and classified accordingly.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('63000000-0000-4000-8000-000000000008','SUBASM-FOUNDATION-BRAKE',
   '基础制动器分总成','Foundation brake subassembly',
   '62000000-0000-4000-8000-000000000006','BRAKING','SUBASSEMBLY',
   'Wheel-end disc or drum braking hardware.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('63000000-0000-4000-8000-000000000009','SUBASM-STEERING-GEAR-COLUMN',
   '转向器及转向柱分总成','Steering gear and column subassembly',
   '62000000-0000-4000-8000-000000000007','STEERING','SUBASSEMBLY',
   'Steering gear, rack or column assembly according to presentation.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('63000000-0000-4000-8000-000000000010','SUBASM-SHOCK-ABSORBER-STRUT',
   '减振器及支柱分总成','Shock absorber and strut subassembly',
   '62000000-0000-4000-8000-000000000008','SUSPENSION','SUBASSEMBLY',
   'Hydraulic or gas suspension damper, including strut configuration where specified.',NULL,
   '{}'::jsonb,'UNKNOWN','[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'MEDIUM',1,'ACTIVE','CANDIDATE')
ON CONFLICT DO NOTHING;

UPDATE customs.customs_classification_unit
SET parent_ccu_id = '63000000-0000-4000-8000-000000000001',
    record_status = 'ACTIVE',
    updated_at = now()
WHERE ccu_code = 'CCU-HV-BATTERY-PACK' AND version = 1;

INSERT INTO customs.customs_classification_unit (
  ccu_id, ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id,
  vehicle_system, unit_level, function_description, material_spec,
  technical_qualifiers, assembly_state, included_items, excluded_items,
  required_input_fields, gri_2a_risk, version, record_status,
  verification_status
) VALUES
  ('64000000-0000-4000-8000-000000000002','CCU-TRACTION-MOTOR',
   '电动汽车驱动电机','Electric vehicle traction motor',
   '63000000-0000-4000-8000-000000000002','ELECTRIC_DRIVE','CUSTOMS_CLASSIFICATION_UNIT',
   'Converts electrical input into propulsion torque.',
   'Electric motor; construction, current type and rated output are classification inputs.',
   '{"current_type":null,"rated_output_kw":null,"integrated_gearbox":null,"integrated_inverter":null}'::jsonb,
   'COMPLETE','["motor_stator","motor_rotor","housing","position_sensor_when_integrated"]'::jsonb,
   '["traction_inverter","reduction_gearbox","drive_axle"]'::jsonb,
   '["part.current_type","part.rated_output_kw","part.integrated_gearbox","part.integrated_inverter","shipment.assembly_state"]'::jsonb,
   'HIGH',1,'ACTIVE','CANDIDATE'),
  ('64000000-0000-4000-8000-000000000003','CCU-TRACTION-INVERTER',
   '驱动逆变器','Traction inverter',
   '63000000-0000-4000-8000-000000000003','POWER_ELECTRONICS','CUSTOMS_CLASSIFICATION_UNIT',
   'Converts DC traction power into controlled motor current.',
   'Static converter using power semiconductor modules.',
   '{"input_voltage_v":null,"output_power_kw":null,"integrated_motor_controller":null,"integrated_dc_dc":null}'::jsonb,
   'COMPLETE','["power_semiconductor_module","control_board","housing","cooling_plate_when_integrated"]'::jsonb,
   '["traction_motor","battery_pack","external_charger"]'::jsonb,
   '["part.primary_function","part.input_voltage_v","part.output_power_kw","part.integrated_functions","shipment.assembly_state"]'::jsonb,
   'HIGH',1,'ACTIVE','CANDIDATE'),
  ('64000000-0000-4000-8000-000000000004','CCU-ONBOARD-CHARGER',
   '车载充电机','On-board charger',
   '63000000-0000-4000-8000-000000000004','POWER_ELECTRONICS','CUSTOMS_CLASSIFICATION_UNIT',
   'Converts external AC input into DC power for charging the traction battery.',
   'Vehicle-mounted static converter.',
   '{"ac_input_phase":null,"rated_power_kw":null,"bidirectional":null,"integrated_dc_dc":null}'::jsonb,
   'COMPLETE','["power_conversion_stage","control_board","housing","cooling_components_when_integrated"]'::jsonb,
   '["offboard_charging_station","charging_cable","traction_battery"]'::jsonb,
   '["part.primary_function","part.ac_input_phase","part.rated_power_kw","part.bidirectional","part.integrated_functions"]'::jsonb,
   'HIGH',1,'ACTIVE','CANDIDATE'),
  ('64000000-0000-4000-8000-000000000005','CCU-DC-DC-CONVERTER',
   '车载直流变换器','Vehicle DC-DC converter',
   '63000000-0000-4000-8000-000000000005','POWER_ELECTRONICS','CUSTOMS_CLASSIFICATION_UNIT',
   'Converts one vehicle DC voltage level to another.',
   'Vehicle-mounted static converter.',
   '{"input_voltage_v":null,"output_voltage_v":null,"rated_power_kw":null,"bidirectional":null,"integrated_charger":null}'::jsonb,
   'COMPLETE','["power_conversion_stage","control_board","housing"]'::jsonb,
   '["traction_inverter","onboard_charger","battery_pack"]'::jsonb,
   '["part.primary_function","part.input_voltage_v","part.output_voltage_v","part.rated_power_kw","part.integrated_functions"]'::jsonb,
   'HIGH',1,'ACTIVE','CANDIDATE'),
  ('64000000-0000-4000-8000-000000000006','CCU-PASSENGER-BODY-SHELL',
   '乘用车车身壳体','Passenger-car body shell',
   '63000000-0000-4000-8000-000000000006','BODY','CUSTOMS_CLASSIFICATION_UNIT',
   'Forms the structural body shell of a passenger motor vehicle.',
   'Primarily welded or joined metal body panels and structural members.',
   '{"vehicle_heading":"8703","with_doors":null,"with_glass":null,"with_interior_trim":null,"painted":null}'::jsonb,
   'INCOMPLETE','["floor_pan","side_structures","roof","pillars","cross_members"]'::jsonb,
   '["chassis_frame_when_separate","powertrain","seats","instrument_panel"]'::jsonb,
   '["vehicle.intended_heading","part.with_doors","part.with_glass","part.with_interior_trim","shipment.assembly_state"]'::jsonb,
   'HIGH',1,'ACTIVE','CANDIDATE'),
  ('64000000-0000-4000-8000-000000000007','CCU-ROAD-WHEEL',
   '机动车道路车轮','Motor-vehicle road wheel',
   '63000000-0000-4000-8000-000000000007','WHEEL_AND_TYRE','CUSTOMS_CLASSIFICATION_UNIT',
   'Supports a tyre and mounts to a motor-vehicle hub.',
   'Steel or aluminium road wheel.',
   '{"material":null,"diameter_inch":null,"with_tyre":null,"with_hub":null}'::jsonb,
   'COMPLETE','["wheel_disc","rim"]'::jsonb,
   '["pneumatic_tyre","wheel_hub","decorative_cover"]'::jsonb,
   '["part.material","part.diameter_inch","part.with_tyre","part.with_hub","vehicle.type"]'::jsonb,
   'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('64000000-0000-4000-8000-000000000008','CCU-FOUNDATION-BRAKE',
   '车轮端基础制动器','Wheel-end foundation brake',
   '63000000-0000-4000-8000-000000000008','BRAKING','CUSTOMS_CLASSIFICATION_UNIT',
   'Applies friction braking force at the wheel end.',
   'Disc or drum brake assembly.',
   '{"brake_type":null,"includes_caliper":null,"includes_disc_or_drum":null,"includes_actuator":null}'::jsonb,
   'COMPLETE','["caliper_or_wheel_cylinder","carrier","pads_or_shoes_when_present"]'::jsonb,
   '["brake_control_ecu","master_cylinder","brake_hose"]'::jsonb,
   '["part.brake_type","part.included_components","vehicle.type","shipment.assembly_state"]'::jsonb,
   'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('64000000-0000-4000-8000-000000000009','CCU-STEERING-GEAR-COLUMN',
   '转向器或转向柱总成','Steering gear or steering column assembly',
   '63000000-0000-4000-8000-000000000009','STEERING','CUSTOMS_CLASSIFICATION_UNIT',
   'Transmits steering input through a steering gear, rack or column.',
   'Mechanical, hydraulic-assisted or electric-assisted steering hardware.',
   '{"component_type":null,"assist_type":null,"includes_electric_motor":null,"includes_ecu":null}'::jsonb,
   'COMPLETE','["steering_gear_or_rack_or_column","housing","assist_components_when_integrated"]'::jsonb,
   '["steering_wheel","road_wheel","separate_control_ecu"]'::jsonb,
   '["part.component_type","part.assist_type","part.includes_electric_motor","part.includes_ecu","vehicle.type"]'::jsonb,
   'MEDIUM',1,'ACTIVE','CANDIDATE'),
  ('64000000-0000-4000-8000-000000000010','CCU-SHOCK-ABSORBER-STRUT',
   '悬架减振器或支柱','Suspension shock absorber or strut',
   '63000000-0000-4000-8000-000000000010','SUSPENSION','CUSTOMS_CLASSIFICATION_UNIT',
   'Damps suspension movement between sprung and unsprung masses.',
   'Hydraulic or gas-filled automotive damper.',
   '{"configuration":null,"electronic_controlled":null,"includes_spring":null,"includes_knuckle":null}'::jsonb,
   'COMPLETE','["damper_body","piston_rod","mounting_eyes_or_strut_mount_when_integrated"]'::jsonb,
   '["coil_spring_when_separate","steering_knuckle","control_ecu"]'::jsonb,
   '["part.configuration","part.electronic_controlled","part.includes_spring","part.includes_knuckle","vehicle.type"]'::jsonb,
   'MEDIUM',1,'ACTIVE','CANDIDATE')
ON CONFLICT DO NOTHING;

INSERT INTO customs.ccu_candidate_hs (
  candidate_id, ccu_id, candidate_rank, hs_nomenclature_version,
  hs6_code, candidate_basis, exclusion_notes, source_clause_id,
  verification_status
) VALUES
  ('65000000-0000-4000-8000-000000000021','64000000-0000-4000-8000-000000000002',1,'HS-2022','850152',
   'Candidate for multi-phase AC traction motors with output exceeding 750 W but not exceeding 75 kW.',
   'Rated output and current type are mandatory; higher-output motors may fall under 850153.',NULL,'CANDIDATE'),
  ('65000000-0000-4000-8000-000000000022','64000000-0000-4000-8000-000000000002',2,'HS-2022','850153',
   'Candidate for multi-phase AC traction motors with output exceeding 75 kW.',
   'Integrated drive units may require essential-character analysis.',NULL,'CANDIDATE'),
  ('65000000-0000-4000-8000-000000000031','64000000-0000-4000-8000-000000000003',1,'HS-2022','850440',
   'Candidate heading for electrical static converters.',
   'Confirm that the inverter is not presented as an inseparable multi-function drive unit.',NULL,'CANDIDATE'),
  ('65000000-0000-4000-8000-000000000041','64000000-0000-4000-8000-000000000004',1,'HS-2022','850440',
   'Candidate heading for vehicle-mounted static converters used for charging.',
   'Exclude off-board charging stations and mere connectors or cables.',NULL,'CANDIDATE'),
  ('65000000-0000-4000-8000-000000000051','64000000-0000-4000-8000-000000000005',1,'HS-2022','850440',
   'Candidate heading for DC static converters.',
   'Integrated multi-function power electronics require principal-function analysis.',NULL,'CANDIDATE'),
  ('65000000-0000-4000-8000-000000000061','64000000-0000-4000-8000-000000000006',1,'HS-2022','870710',
   'Candidate for bodies, including cabs, for motor vehicles of heading 8703.',
   'Confirm intended vehicle heading and whether presentation has the essential character of a complete vehicle.',NULL,'CANDIDATE'),
  ('65000000-0000-4000-8000-000000000071','64000000-0000-4000-8000-000000000007',1,'HS-2022','870870',
   'Candidate for road wheels and parts and accessories thereof.',
   'Tyres, hubs and wheel covers may be classified separately depending on presentation.',NULL,'CANDIDATE'),
  ('65000000-0000-4000-8000-000000000081','64000000-0000-4000-8000-000000000008',1,'HS-2022','870830',
   'Candidate for brakes and servo-brakes and their parts.',
   'Separate electronic controllers, hoses and friction material may fall in other headings.',NULL,'CANDIDATE'),
  ('65000000-0000-4000-8000-000000000091','64000000-0000-4000-8000-000000000009',1,'HS-2022','870894',
   'Candidate for steering wheels, steering columns and steering boxes, and parts thereof.',
   'Separate electric motors or electronic controllers require specific-heading review.',NULL,'CANDIDATE'),
  ('65000000-0000-4000-8000-000000000101','64000000-0000-4000-8000-000000000010',1,'HS-2022','870880',
   'Candidate for suspension systems and parts, including shock absorbers.',
   'Springs and separately presented control electronics may fall in specific headings.',NULL,'CANDIDATE')
ON CONFLICT DO NOTHING;

-- Every leaf CCU receives the three mandatory screening tags.
INSERT INTO customs.ccu_risk_tag (
  ccu_risk_tag_id, ccu_id, risk_tag_type, risk_level,
  trigger_condition, risk_note, source_clause_id, verification_status
)
SELECT
  gen_random_uuid(), c.ccu_id, t.risk_tag_type,
  CASE
    WHEN t.risk_tag_type = 'GRI_2A' THEN c.gri_2a_risk
    WHEN t.risk_tag_type = 'HEADING_8708_EXCLUSION'
         AND c.ccu_code IN ('CCU-HV-BATTERY-PACK','CCU-TRACTION-MOTOR',
                            'CCU-TRACTION-INVERTER','CCU-ONBOARD-CHARGER',
                            'CCU-DC-DC-CONVERTER') THEN 'HIGH'::ref.risk_level
    WHEN t.risk_tag_type = 'AP_REGULATORY' THEN 'MEDIUM'::ref.risk_level
    ELSE 'LOW'::ref.risk_level
  END,
  CASE t.risk_tag_type
    WHEN 'GRI_2A'
      THEN '{"field":"shipment.assembly_state","operator":"NE","value":"COMPLETE"}'::jsonb
    WHEN 'HEADING_8708_EXCLUSION'
      THEN '{"field":"classification.specific_heading_review_completed","operator":"EQ","value":false}'::jsonb
    ELSE '{"field":"scenario.import_mode","operator":"IN","value":["CKD","SKD"]}'::jsonb
  END,
  CASE t.risk_tag_type
    WHEN 'GRI_2A'
      THEN 'Assess incomplete, unassembled or combined presentation under GRI 2(a); do not automatically classify as a complete vehicle.'
    WHEN 'HEADING_8708_EXCLUSION'
      THEN 'Review Section XVII exclusions and any more specific material, electrical or mechanical heading before using heading 8708.'
    ELSE 'Check MITI AP and programme-level import controls when the unit is shipped as part of a CKD or SKD vehicle set.'
  END,
  CASE
    WHEN t.risk_tag_type = 'GRI_2A'
      THEN '40000000-0000-4000-8000-000000000002'::uuid
    WHEN t.risk_tag_type = 'AP_REGULATORY'
      THEN '40000000-0000-4000-8000-000000000003'::uuid
    ELSE NULL
  END,
  'CANDIDATE'::ref.verification_status
FROM customs.customs_classification_unit c
CROSS JOIN (
  VALUES
    ('GRI_2A'::ref.risk_tag_type),
    ('HEADING_8708_EXCLUSION'::ref.risk_tag_type),
    ('AP_REGULATORY'::ref.risk_tag_type)
) AS t(risk_tag_type)
WHERE c.unit_level = 'CUSTOMS_CLASSIFICATION_UNIT'
  AND c.ccu_code IN (
    'CCU-HV-BATTERY-PACK','CCU-TRACTION-MOTOR','CCU-TRACTION-INVERTER',
    'CCU-ONBOARD-CHARGER','CCU-DC-DC-CONVERTER',
    'CCU-PASSENGER-BODY-SHELL','CCU-ROAD-WHEEL','CCU-FOUNDATION-BRAKE',
    'CCU-STEERING-GEAR-COLUMN','CCU-SHOCK-ABSORBER-STRUT'
  )
ON CONFLICT (ccu_id, risk_tag_type) DO NOTHING;

INSERT INTO audit.missing_data (
  missing_data_id, calculation_run_id, field_path, description,
  data_owner, data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
)
SELECT
  gen_random_uuid(), NULL,
  'customs.tariff_mapping[' || c.ccu_code || '].national_tariff_code',
  'Malaysia PDK 2025 national tariff mapping has not yet been verified for this CCU.',
  'CUSTOMS_CLASSIFICATION_OWNER', 'PUBLIC_RESEARCH', 'PUBLIC',
  'MALAYSIA_TARIFF_MAPPING_FOR_' || c.ccu_code, 'P1',
  'Verify technical inputs, candidate HS6 and the exact PDK 2025 national tariff line before attaching rates.',
  'https://ezhs.customs.gov.my/', 'OPEN'
FROM customs.customs_classification_unit c
WHERE c.unit_level = 'CUSTOMS_CLASSIFICATION_UNIT'
  AND c.ccu_code IN (
    'CCU-TRACTION-MOTOR','CCU-TRACTION-INVERTER','CCU-ONBOARD-CHARGER',
    'CCU-DC-DC-CONVERTER','CCU-PASSENGER-BODY-SHELL','CCU-ROAD-WHEEL',
    'CCU-FOUNDATION-BRAKE','CCU-STEERING-GEAR-COLUMN',
    'CCU-SHOCK-ABSORBER-STRUT'
  )
  AND NOT EXISTS (
    SELECT 1
    FROM audit.missing_data m
    WHERE m.field_path =
      'customs.tariff_mapping[' || c.ccu_code || '].national_tariff_code'
  );

COMMIT;
