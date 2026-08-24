BEGIN;

-- Phase 1 CCU 21-60. These are generic customs-classification units, not
-- enterprise part numbers. Technical values remain unpopulated until use.

WITH new_systems (ccu_code, name_cn, name_en, vehicle_system) AS (
  VALUES
    ('SYS-ICE-POWERTRAIN','内燃机动力系统','Internal-combustion powertrain','ICE_POWERTRAIN'),
    ('SYS-FUEL','燃油系统','Fuel system','FUEL_SYSTEM'),
    ('SYS-EXHAUST-AFTERTREATMENT','排气及后处理系统','Exhaust and aftertreatment','EXHAUST_AFTERTREATMENT'),
    ('SYS-INFOTAINMENT','信息娱乐系统','Infotainment system','INFOTAINMENT')
)
INSERT INTO customs.customs_classification_unit (
  ccu_code, ccu_name_cn, ccu_name_en, vehicle_system, unit_level,
  function_description, technical_qualifiers, assembly_state,
  included_items, excluded_items, required_input_fields, gri_2a_risk,
  version, record_status, verification_status
)
SELECT ccu_code, name_cn, name_en, vehicle_system,
       'VEHICLE_SYSTEM'::ref.ccu_unit_level,
       'Phase 1 generic vehicle-system hierarchy node.',
       '{}'::jsonb, 'UNKNOWN'::ref.assembly_state,
       '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 'LOW'::ref.risk_level,
       1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
FROM new_systems
ON CONFLICT DO NOTHING;

WITH groups (group_code, name_cn, name_en, parent_code, vehicle_system) AS (
  VALUES
    ('TYRE','轮胎','Tyre','SYS-CHASSIS','WHEEL_AND_TYRE'),
    ('ICE','内燃机','Internal-combustion engine','SYS-ICE-POWERTRAIN','ICE_POWERTRAIN'),
    ('FUEL','燃油供给','Fuel supply','SYS-FUEL','FUEL_SYSTEM'),
    ('EXHAUST','排气及后处理','Exhaust and aftertreatment','SYS-EXHAUST-AFTERTREATMENT','EXHAUST_AFTERTREATMENT'),
    ('ICE-ELECTRICAL','发动机电气','Engine electrical','SYS-VEHICLE-ELECTRICAL','ICE_ELECTRICAL'),
    ('VEHICLE-ELECTRONICS','车辆电子控制','Vehicle electronic control','SYS-VEHICLE-ELECTRICAL','VEHICLE_ELECTRONICS'),
    ('INFOTAINMENT','车载信息娱乐','Vehicle infotainment','SYS-INFOTAINMENT','INFOTAINMENT'),
    ('VISIBILITY','视野辅助','Visibility equipment','SYS-VISIBILITY-LIGHTING','VISIBILITY_LIGHTING'),
    ('THERMAL','车辆热管理','Vehicle thermal management','SYS-THERMAL-MANAGEMENT','THERMAL_MANAGEMENT'),
    ('BRAKING','制动部件','Braking components','SYS-CHASSIS','BRAKING'),
    ('SUSPENSION','悬架部件','Suspension components','SYS-CHASSIS','SUSPENSION'),
    ('BODY','车身部件','Body components','SYS-BODY','BODY'),
    ('DRIVELINE','传动部件','Driveline components','SYS-DRIVELINE','DRIVELINE'),
    ('STEERING','转向部件','Steering components','SYS-CHASSIS','STEERING')
),
assemblies AS (
  INSERT INTO customs.customs_classification_unit (
    ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id, vehicle_system,
    unit_level, function_description, technical_qualifiers, assembly_state,
    included_items, excluded_items, required_input_fields, gri_2a_risk,
    version, record_status, verification_status
  )
  SELECT 'ASM-P1-' || g.group_code, g.name_cn || '总成', g.name_en || ' assembly',
         parent.ccu_id, g.vehicle_system, 'ASSEMBLY'::ref.ccu_unit_level,
         'Phase 1 generic assembly hierarchy node.', '{}'::jsonb,
         'UNKNOWN'::ref.assembly_state, '[]'::jsonb, '[]'::jsonb,
         '[]'::jsonb, 'LOW'::ref.risk_level, 1, 'ACTIVE', 'CANDIDATE'
  FROM groups g
  JOIN customs.customs_classification_unit parent
    ON parent.ccu_code=g.parent_code AND parent.version=1
  ON CONFLICT DO NOTHING
  RETURNING ccu_id
)
SELECT count(*) FROM assemblies;

WITH groups (group_code, name_cn, name_en, vehicle_system) AS (
  VALUES
    ('TYRE','轮胎','Tyre','WHEEL_AND_TYRE'),
    ('ICE','内燃机','Internal-combustion engine','ICE_POWERTRAIN'),
    ('FUEL','燃油供给','Fuel supply','FUEL_SYSTEM'),
    ('EXHAUST','排气及后处理','Exhaust and aftertreatment','EXHAUST_AFTERTREATMENT'),
    ('ICE-ELECTRICAL','发动机电气','Engine electrical','ICE_ELECTRICAL'),
    ('VEHICLE-ELECTRONICS','车辆电子控制','Vehicle electronic control','VEHICLE_ELECTRONICS'),
    ('INFOTAINMENT','车载信息娱乐','Vehicle infotainment','INFOTAINMENT'),
    ('VISIBILITY','视野辅助','Visibility equipment','VISIBILITY_LIGHTING'),
    ('THERMAL','车辆热管理','Vehicle thermal management','THERMAL_MANAGEMENT'),
    ('BRAKING','制动部件','Braking components','BRAKING'),
    ('SUSPENSION','悬架部件','Suspension components','SUSPENSION'),
    ('BODY','车身部件','Body components','BODY'),
    ('DRIVELINE','传动部件','Driveline components','DRIVELINE'),
    ('STEERING','转向部件','Steering components','STEERING')
)
INSERT INTO customs.customs_classification_unit (
  ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id, vehicle_system,
  unit_level, function_description, technical_qualifiers, assembly_state,
  included_items, excluded_items, required_input_fields, gri_2a_risk,
  version, record_status, verification_status
)
SELECT 'SUBASM-P1-' || g.group_code, g.name_cn || '分总成',
       g.name_en || ' subassembly', parent.ccu_id, g.vehicle_system,
       'SUBASSEMBLY'::ref.ccu_unit_level,
       'Phase 1 generic subassembly hierarchy node.', '{}'::jsonb,
       'UNKNOWN'::ref.assembly_state, '[]'::jsonb, '[]'::jsonb,
       '[]'::jsonb, 'LOW'::ref.risk_level, 1, 'ACTIVE', 'CANDIDATE'
FROM groups g
JOIN customs.customs_classification_unit parent
  ON parent.ccu_code='ASM-P1-' || g.group_code AND parent.version=1
ON CONFLICT DO NOTHING;

WITH units (
  seq, ccu_code, name_cn, name_en, group_code, vehicle_system,
  hs6_codes, required_fields
) AS (
  VALUES
    (21,'CCU-PASSENGER-CAR-TYRE','乘用车充气轮胎','Passenger-car pneumatic tyre','TYRE','WHEEL_AND_TYRE','["401110"]'::jsonb,'["vehicle.intended_heading","part.new_or_used","part.pneumatic","part.tyre_size","shipment.assembly_state"]'::jsonb),
    (22,'CCU-SPARK-IGNITION-ENGINE','乘用车点燃式活塞发动机','Spark-ignition vehicle engine','ICE','ICE_POWERTRAIN','["840734"]','["vehicle.intended_heading","engine.ignition_type","engine.displacement_cc","engine.complete_engine","shipment.assembly_state"]'),
    (23,'CCU-DIESEL-VEHICLE-ENGINE','机动车压燃式活塞发动机','Diesel vehicle engine','ICE','ICE_POWERTRAIN','["840820"]','["vehicle.intended_heading","engine.ignition_type","engine.displacement_cc","engine.complete_engine","shipment.assembly_state"]'),
    (24,'CCU-ENGINE-BLOCK-OR-HEAD','发动机缸体或缸盖','Engine block or cylinder head','ICE','ICE_POWERTRAIN','["840991","840999"]','["vehicle.intended_heading","engine.ignition_type","engine.parent_engine_heading","part.block_or_head","shipment.assembly_state"]'),
    (25,'CCU-ENGINE-FUEL-PUMP','发动机燃油泵','Engine fuel pump','FUEL','FUEL_SYSTEM','["841330"]','["vehicle.intended_heading","part.pump_function","part.engine_mounted","part.electrically_operated","shipment.assembly_state"]'),
    (26,'CCU-ENGINE-OIL-FILTER','发动机机油滤清器','Engine oil filter','ICE','ICE_POWERTRAIN','["842123"]','["vehicle.intended_heading","engine.ignition_type","part.filter_medium","part.complete_filter","shipment.assembly_state"]'),
    (27,'CCU-ENGINE-INTAKE-AIR-FILTER','发动机进气滤清器','Engine intake-air filter','ICE','ICE_POWERTRAIN','["842131"]','["vehicle.intended_heading","part.primary_function","part.complete_filter","part.filter_medium","shipment.assembly_state"]'),
    (28,'CCU-CATALYTIC-CONVERTER','机动车尾气催化转化器','Vehicle catalytic converter','EXHAUST','EXHAUST_AFTERTREATMENT','["842132"]','["part.catalytic_or_particulate","part.complete_unit","engine.fuel_type","part.combined_functions","shipment.assembly_state"]'),
    (29,'CCU-EXHAUST-SILENCER-PIPE','消声器及排气管','Exhaust silencer or pipe','EXHAUST','EXHAUST_AFTERTREATMENT','["870892"]','["vehicle.intended_heading","part.presentation_scope","part.silencer_or_pipe","part.complete_or_part","shipment.assembly_state"]'),
    (30,'CCU-VEHICLE-FUEL-TANK','机动车燃油箱','Vehicle fuel tank','FUEL','FUEL_SYSTEM','["870899"]','["vehicle.intended_heading","part.fuel_tank_confirmed","part.assembled_state","part.material","shipment.assembly_state"]'),
    (31,'CCU-ENGINE-FUEL-INJECTOR','发动机燃油喷射器','Engine fuel injector','FUEL','FUEL_SYSTEM','["840991","840999"]','["vehicle.intended_heading","engine.ignition_type","engine.parent_engine_heading","part.injector_type","shipment.assembly_state"]'),
    (32,'CCU-SPARK-PLUG','火花塞','Spark plug','ICE-ELECTRICAL','ICE_ELECTRICAL','["851110"]','["part.spark_plug_confirmed","part.engine_use","vehicle.intended_heading","part.technical_standard","shipment.assembly_state"]'),
    (33,'CCU-IGNITION-COIL-DISTRIBUTOR','点火线圈或分电器','Ignition coil or distributor','ICE-ELECTRICAL','ICE_ELECTRICAL','["851130"]','["part.coil_or_distributor","part.assembled_state","vehicle.intended_heading","part.operating_voltage_v","shipment.assembly_state"]'),
    (34,'CCU-STARTER-MOTOR','起动电机','Starter motor','ICE-ELECTRICAL','ICE_ELECTRICAL','["851140"]','["vehicle.intended_heading","part.starter_confirmed","part.motor_technology","part.rated_output_kw","shipment.assembly_state"]'),
    (35,'CCU-VEHICLE-ALTERNATOR','机动车交流发电机','Vehicle alternator','ICE-ELECTRICAL','ICE_ELECTRICAL','["851150"]','["vehicle.intended_heading","part.generator_type","part.voltage_v","part.rated_output_kw","shipment.assembly_state"]'),
    (36,'CCU-VEHICLE-CONTROL-ECU','机动车电子控制单元','Vehicle electronic control unit','VEHICLE-ELECTRONICS','VEHICLE_ELECTRONICS','["853710","903289"]','["part.primary_function","part.controlled_system","part.operating_voltage_v","part.automatic_regulation","shipment.assembly_state"]'),
    (37,'CCU-INSTRUMENT-CLUSTER','机动车仪表总成','Vehicle instrument cluster','VEHICLE-ELECTRONICS','VEHICLE_ELECTRONICS','["902920","853120"]','["part.primary_function","part.display_type","part.speedometer_function","part.tachometer_function","shipment.assembly_state"]'),
    (38,'CCU-VEHICLE-INFOTAINMENT-HEAD-UNIT','车载信息娱乐主机','Vehicle infotainment head unit','INFOTAINMENT','INFOTAINMENT','["852721"]','["part.radio_receiver","part.digital_radio_data_decode","part.integrated_navigation","part.integrated_display","shipment.assembly_state"]'),
    (39,'CCU-VEHICLE-LOUDSPEAKER','机动车扬声器总成','Vehicle loudspeaker','INFOTAINMENT','INFOTAINMENT','["851829"]','["part.with_enclosure","part.frequency_range","part.diameter_mm","part.telecommunication_use","shipment.assembly_state"]'),
    (40,'CCU-REAR-VIEW-MIRROR','机动车后视镜','Vehicle rear-view mirror','VISIBILITY','VISIBILITY_LIGHTING','["700910"]','["part.rear_view_mirror","part.integrated_camera","part.integrated_display","vehicle.intended_heading","shipment.assembly_state"]'),
    (41,'CCU-WINDSCREEN-WIPER','风挡刮水器','Windscreen wiper','VISIBILITY','VISIBILITY_LIGHTING','["851240"]','["part.primary_function","part.complete_wiper","part.motor_included","vehicle.intended_heading","shipment.assembly_state"]'),
    (42,'CCU-VEHICLE-HORN','机动车喇叭','Vehicle horn','VISIBILITY','VISIBILITY_LIGHTING','["851230"]','["part.horn_or_other_signal","part.assembled_state","part.sound_type","vehicle.intended_heading","shipment.assembly_state"]'),
    (43,'CCU-VEHICLE-HVAC-UNIT','机动车空调机组','Vehicle HVAC unit','THERMAL','THERMAL_MANAGEMENT','["841520"]','["part.vehicle_air_conditioner","part.cooling_capacity_kw","part.heating_function","part.complete_unit","shipment.assembly_state"]'),
    (44,'CCU-VEHICLE-COOLANT-PUMP','机动车冷却液泵','Vehicle coolant pump','THERMAL','THERMAL_MANAGEMENT','["841330","841381"]','["part.primary_function","part.engine_mounted","part.electrically_operated","part.flow_rate_m3h","shipment.assembly_state"]'),
    (45,'CCU-BRAKE-FRICTION-PAD-LINING','制动摩擦片或衬片','Brake friction pad or lining','BRAKING','BRAKING','["681381"]','["part.pad_or_lining","part.material","part.mounted_or_unmounted","vehicle.intended_heading","shipment.assembly_state"]'),
    (46,'CCU-BRAKE-MASTER-CYLINDER','制动主缸','Brake master cylinder','BRAKING','BRAKING','["870830"]','["vehicle.intended_heading","part.master_cylinder_confirmed","part.complete_or_part","part.includes_reservoir","shipment.assembly_state"]'),
    (47,'CCU-BRAKE-HOSE-ASSEMBLY','制动软管总成','Brake hose assembly','BRAKING','BRAKING','["400932"]','["part.rubber_hose","part.reinforcement_material","part.with_fittings","part.brake_use","shipment.assembly_state"]'),
    (48,'CCU-SUSPENSION-COIL-SPRING','悬架螺旋弹簧','Suspension coil spring','SUSPENSION','SUSPENSION','["732020"]','["part.helical_spring","part.iron_or_steel","part.vehicle_use","vehicle.intended_heading","shipment.assembly_state"]'),
    (49,'CCU-SUSPENSION-LEAF-SPRING','悬架钢板弹簧','Suspension leaf spring','SUSPENSION','SUSPENSION','["732010"]','["part.leaf_spring","part.iron_or_steel","part.vehicle_use","vehicle.intended_heading","shipment.assembly_state"]'),
    (50,'CCU-SUSPENSION-CONTROL-ARM','悬架控制臂','Suspension control arm','SUSPENSION','SUSPENSION','["870880"]','["part.presentation_scope","part.control_arm_confirmed","vehicle.intended_heading","part.integrated_ball_joint","shipment.assembly_state"]'),
    (51,'CCU-STABILIZER-BAR','悬架稳定杆','Suspension stabilizer bar','SUSPENSION','SUSPENSION','["870880"]','["part.presentation_scope","part.stabilizer_bar_confirmed","vehicle.intended_heading","part.material","shipment.assembly_state"]'),
    (52,'CCU-VEHICLE-DOOR-ASSEMBLY','机动车车门总成','Vehicle door assembly','BODY','BODY','["870829"]','["vehicle.intended_heading","part.complete_door","part.with_glass","part.with_trim","shipment.assembly_state"]'),
    (53,'CCU-VEHICLE-HOOD-BONNET','机动车发动机罩','Vehicle hood or bonnet','BODY','BODY','["870829"]','["vehicle.intended_heading","part.hood_panel_or_rod","part.material","part.with_hinges","shipment.assembly_state"]'),
    (54,'CCU-VEHICLE-FENDER-PANEL','机动车翼子板','Vehicle fender panel','BODY','BODY','["870829"]','["vehicle.intended_heading","part.fender_or_mudguard","part.material","part.finished_state","shipment.assembly_state"]'),
    (55,'CCU-INSTRUMENT-PANEL-DASHBOARD','仪表板骨架或总成','Instrument panel or dashboard','BODY','BODY','["870829"]','["vehicle.intended_heading","part.structural_or_trim","part.integrated_equipment","part.material","shipment.assembly_state"]'),
    (56,'CCU-POWER-WINDOW-REGULATOR-MOTOR','电动车窗升降器或电机','Power-window regulator or motor','BODY','BODY','["870829","850131"]','["vehicle.intended_heading","part.motor_only","part.regulator_included","part.rated_output_w","shipment.assembly_state"]'),
    (57,'CCU-VEHICLE-GEARBOX-TRANSMISSION','机动车变速器','Vehicle gearbox or transmission','DRIVELINE','DRIVELINE','["870840"]','["vehicle.intended_heading","part.transmission_type","part.complete_gearbox","part.integrated_motor","shipment.assembly_state"]'),
    (58,'CCU-VEHICLE-CLUTCH','机动车离合器','Vehicle clutch','DRIVELINE','DRIVELINE','["870893"]','["vehicle.intended_heading","part.complete_clutch","part.friction_or_other","part.integrated_actuator","shipment.assembly_state"]'),
    (59,'CCU-PROPELLER-DRIVE-SHAFT','传动轴','Propeller or drive shaft','DRIVELINE','DRIVELINE','["870899"]','["vehicle.intended_heading","part.drive_shaft_confirmed","part.front_or_rear","part.complete_or_part","shipment.assembly_state"]'),
    (60,'CCU-STEERING-WHEEL','机动车方向盘','Vehicle steering wheel','STEERING','STEERING','["870894"]','["vehicle.intended_heading","part.steering_wheel_or_other_part","part.integrated_airbag","part.integrated_controls","shipment.assembly_state"]')
),
inserted AS (
  INSERT INTO customs.customs_classification_unit (
    ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id, vehicle_system,
    unit_level, function_description, material_spec, technical_qualifiers,
    assembly_state, included_items, excluded_items, required_input_fields,
    gri_2a_risk, version, record_status, verification_status
  )
  SELECT u.ccu_code, u.name_cn, u.name_en, parent.ccu_id, u.vehicle_system,
         'CUSTOMS_CLASSIFICATION_UNIT'::ref.ccu_unit_level,
         'Generic customs-classification unit; enterprise configuration is supplied at use time.',
         NULL, '{}'::jsonb, 'UNKNOWN'::ref.assembly_state,
         '[]'::jsonb, '[]'::jsonb, u.required_fields,
         'MEDIUM'::ref.risk_level, 1, 'ACTIVE', 'CANDIDATE'
  FROM units u
  JOIN customs.customs_classification_unit parent
    ON parent.ccu_code='SUBASM-P1-' || u.group_code AND parent.version=1
  ON CONFLICT DO NOTHING
  RETURNING ccu_id
)
SELECT count(*) FROM inserted;

WITH units (ccu_code, hs6_codes) AS (
  VALUES
    ('CCU-PASSENGER-CAR-TYRE','["401110"]'::jsonb),('CCU-SPARK-IGNITION-ENGINE','["840734"]'),
    ('CCU-DIESEL-VEHICLE-ENGINE','["840820"]'),('CCU-ENGINE-BLOCK-OR-HEAD','["840991","840999"]'),
    ('CCU-ENGINE-FUEL-PUMP','["841330"]'),('CCU-ENGINE-OIL-FILTER','["842123"]'),
    ('CCU-ENGINE-INTAKE-AIR-FILTER','["842131"]'),('CCU-CATALYTIC-CONVERTER','["842132"]'),
    ('CCU-EXHAUST-SILENCER-PIPE','["870892"]'),('CCU-VEHICLE-FUEL-TANK','["870899"]'),
    ('CCU-ENGINE-FUEL-INJECTOR','["840991","840999"]'),('CCU-SPARK-PLUG','["851110"]'),
    ('CCU-IGNITION-COIL-DISTRIBUTOR','["851130"]'),('CCU-STARTER-MOTOR','["851140"]'),
    ('CCU-VEHICLE-ALTERNATOR','["851150"]'),('CCU-VEHICLE-CONTROL-ECU','["853710","903289"]'),
    ('CCU-INSTRUMENT-CLUSTER','["902920","853120"]'),('CCU-VEHICLE-INFOTAINMENT-HEAD-UNIT','["852721"]'),
    ('CCU-VEHICLE-LOUDSPEAKER','["851829"]'),('CCU-REAR-VIEW-MIRROR','["700910"]'),
    ('CCU-WINDSCREEN-WIPER','["851240"]'),('CCU-VEHICLE-HORN','["851230"]'),
    ('CCU-VEHICLE-HVAC-UNIT','["841520"]'),('CCU-VEHICLE-COOLANT-PUMP','["841330","841381"]'),
    ('CCU-BRAKE-FRICTION-PAD-LINING','["681381"]'),('CCU-BRAKE-MASTER-CYLINDER','["870830"]'),
    ('CCU-BRAKE-HOSE-ASSEMBLY','["400932"]'),('CCU-SUSPENSION-COIL-SPRING','["732020"]'),
    ('CCU-SUSPENSION-LEAF-SPRING','["732010"]'),('CCU-SUSPENSION-CONTROL-ARM','["870880"]'),
    ('CCU-STABILIZER-BAR','["870880"]'),('CCU-VEHICLE-DOOR-ASSEMBLY','["870829"]'),
    ('CCU-VEHICLE-HOOD-BONNET','["870829"]'),('CCU-VEHICLE-FENDER-PANEL','["870829"]'),
    ('CCU-INSTRUMENT-PANEL-DASHBOARD','["870829"]'),('CCU-POWER-WINDOW-REGULATOR-MOTOR','["870829","850131"]'),
    ('CCU-VEHICLE-GEARBOX-TRANSMISSION','["870840"]'),('CCU-VEHICLE-CLUTCH','["870893"]'),
    ('CCU-PROPELLER-DRIVE-SHAFT','["870899"]'),('CCU-STEERING-WHEEL','["870894"]')
),
expanded AS (
  SELECT u.ccu_code, h.hs6_code, h.ordinality::integer AS candidate_rank
  FROM units u
  CROSS JOIN LATERAL jsonb_array_elements_text(u.hs6_codes)
    WITH ORDINALITY h(hs6_code, ordinality)
)
INSERT INTO customs.ccu_candidate_hs (
  ccu_id, candidate_rank, hs_nomenclature_version, hs6_code,
  candidate_basis, exclusion_notes, verification_status
)
SELECT c.ccu_id, e.candidate_rank, 'HS-2022', e.hs6_code,
       'Phase 1 generic candidate route; national-line selection is conditional.',
       'Apply legal notes, specific-heading review and enterprise technical facts.',
       'CANDIDATE'
FROM expanded e
JOIN customs.customs_classification_unit c
  ON c.ccu_code=e.ccu_code AND c.version=1
WHERE NOT EXISTS (
  SELECT 1 FROM customs.ccu_candidate_hs existing
  WHERE existing.ccu_id=c.ccu_id
    AND existing.candidate_rank=e.candidate_rank
    AND existing.hs6_code=e.hs6_code
);

INSERT INTO customs.ccu_risk_tag (
  ccu_risk_tag_id, ccu_id, risk_tag_type, risk_level,
  trigger_condition, risk_note, verification_status
)
SELECT gen_random_uuid(), c.ccu_id, t.risk_tag_type,
       'MEDIUM'::ref.risk_level,
       CASE t.risk_tag_type
         WHEN 'GRI_2A' THEN '{"field":"shipment.assembly_state","operator":"NE","value":"COMPLETE"}'::jsonb
         WHEN 'HEADING_8708_EXCLUSION' THEN '{"field":"classification.specific_heading_review_completed","operator":"EQ","value":false}'::jsonb
         ELSE '{"field":"scenario.import_mode","operator":"IN","value":["CKD","SKD"]}'::jsonb
       END,
       CASE t.risk_tag_type
         WHEN 'GRI_2A' THEN 'Review incomplete or unassembled presentation under GRI 2(a).'
         WHEN 'HEADING_8708_EXCLUSION' THEN 'Review Section XVII exclusions and more specific headings.'
         ELSE 'Evaluate programme-level AP and other import controls separately.'
       END,
       'CANDIDATE'
FROM customs.customs_classification_unit c
CROSS JOIN (
  VALUES ('GRI_2A'::ref.risk_tag_type),
         ('HEADING_8708_EXCLUSION'::ref.risk_tag_type),
         ('AP_REGULATORY'::ref.risk_tag_type)
) t(risk_tag_type)
WHERE EXISTS (
  SELECT 1
  FROM customs.ccu_candidate_hs candidate
  WHERE candidate.ccu_id=c.ccu_id
    AND candidate.candidate_basis =
      'Phase 1 generic candidate route; national-line selection is conditional.'
)
AND NOT EXISTS (
  SELECT 1 FROM customs.ccu_risk_tag x
  WHERE x.ccu_id=c.ccu_id AND x.risk_tag_type=t.risk_tag_type
);

COMMIT;
