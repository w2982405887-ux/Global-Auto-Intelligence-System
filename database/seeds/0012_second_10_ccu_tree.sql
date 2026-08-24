BEGIN;

-- Phase 1.6: second batch of stable customs-classification units.
-- Enterprise-specific facts stay NULL and are required only when a real part
-- is linked and used in a classification/calculation.

WITH rows (
  ccu_id, ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id,
  vehicle_system, unit_level, function_description
) AS (
  VALUES
    ('61100000-0000-4000-8000-000000000001'::uuid,'SYS-VEHICLE-ELECTRICAL','低压电气系统','Vehicle electrical system',NULL::uuid,'VEHICLE_ELECTRICAL','VEHICLE_SYSTEM','Distributes low-voltage power and electrical signals.'),
    ('61100000-0000-4000-8000-000000000002'::uuid,'SYS-OCCUPANT-SAFETY','乘员安全系统','Occupant safety system',NULL::uuid,'OCCUPANT_SAFETY','VEHICLE_SYSTEM','Provides occupant restraint and crash protection.'),
    ('61100000-0000-4000-8000-000000000003'::uuid,'SYS-INTERIOR','内饰系统','Interior system',NULL::uuid,'INTERIOR','VEHICLE_SYSTEM','Provides seating and occupant accommodation.'),
    ('61100000-0000-4000-8000-000000000004'::uuid,'SYS-VISIBILITY-LIGHTING','视野及照明系统','Visibility and lighting system',NULL::uuid,'VISIBILITY_LIGHTING','VEHICLE_SYSTEM','Provides glazing, road illumination and signalling.'),
    ('61100000-0000-4000-8000-000000000005'::uuid,'SYS-THERMAL-MANAGEMENT','热管理系统','Thermal management system',NULL::uuid,'THERMAL_MANAGEMENT','VEHICLE_SYSTEM','Controls cabin and powertrain thermal conditions.'),
    ('61100000-0000-4000-8000-000000000006'::uuid,'SYS-DRIVELINE','传动系统','Driveline system',NULL::uuid,'DRIVELINE','VEHICLE_SYSTEM','Transfers propulsion torque to the road wheels.'),

    ('62100000-0000-4000-8000-000000000001','ASM-WIRING-DISTRIBUTION','线束配电总成','Wiring distribution assembly','61100000-0000-4000-8000-000000000001','VEHICLE_ELECTRICAL','ASSEMBLY','Distributes vehicle power and signals.'),
    ('62100000-0000-4000-8000-000000000002','ASM-AIRBAG-RESTRAINT','安全气囊总成','Airbag restraint assembly','61100000-0000-4000-8000-000000000002','OCCUPANT_SAFETY','ASSEMBLY','Provides inflatable crash restraint.'),
    ('62100000-0000-4000-8000-000000000003','ASM-SEAT','座椅总成','Seat assembly','61100000-0000-4000-8000-000000000003','INTERIOR','ASSEMBLY','Supports and positions vehicle occupants.'),
    ('62100000-0000-4000-8000-000000000004','ASM-GLAZING','汽车玻璃总成','Vehicle glazing assembly','61100000-0000-4000-8000-000000000004','VISIBILITY_LIGHTING','ASSEMBLY','Provides transparent vehicle enclosure and visibility.'),
    ('62100000-0000-4000-8000-000000000005','ASM-LIGHTING-SIGNALLING','照明信号总成','Lighting and signalling assembly','61100000-0000-4000-8000-000000000004','VISIBILITY_LIGHTING','ASSEMBLY','Provides vehicle lighting and visual signalling.'),
    ('62100000-0000-4000-8000-000000000006','ASM-AIR-CONDITIONING','空调总成','Air-conditioning assembly','61100000-0000-4000-8000-000000000005','THERMAL_MANAGEMENT','ASSEMBLY','Provides cabin refrigeration and climate control.'),
    ('62100000-0000-4000-8000-000000000007','ASM-DRIVE-AXLE','驱动桥总成','Drive axle assembly','61100000-0000-4000-8000-000000000006','DRIVELINE','ASSEMBLY','Transfers torque through differential and axle elements.'),
    ('62100000-0000-4000-8000-000000000008','ASM-BUMPER','保险杠总成','Bumper assembly','61000000-0000-4000-8000-000000000002','BODY','ASSEMBLY','Provides exterior low-speed impact protection.'),
    ('62100000-0000-4000-8000-000000000009','ASM-SEAT-BELT','安全带总成','Seat-belt assembly','61100000-0000-4000-8000-000000000002','OCCUPANT_SAFETY','ASSEMBLY','Restrains occupants using webbing and locking hardware.'),
    ('62100000-0000-4000-8000-000000000010','ASM-RADIATOR','散热器总成','Radiator assembly','61100000-0000-4000-8000-000000000005','THERMAL_MANAGEMENT','ASSEMBLY','Rejects vehicle-system heat to ambient air.'),

    ('63100000-0000-4000-8000-000000000001','SUBASM-VEHICLE-WIRING-HARNESS','整车线束分总成','Vehicle wiring harness subassembly','62100000-0000-4000-8000-000000000001','VEHICLE_ELECTRICAL','SUBASSEMBLY','Assembled insulated conductors with terminals and connectors.'),
    ('63100000-0000-4000-8000-000000000002','SUBASM-AIRBAG','安全气囊分总成','Airbag subassembly','62100000-0000-4000-8000-000000000002','OCCUPANT_SAFETY','SUBASSEMBLY','Airbag module or separately presented parts.'),
    ('63100000-0000-4000-8000-000000000003','SUBASM-VEHICLE-SEAT','机动车座椅分总成','Motor-vehicle seat subassembly','62100000-0000-4000-8000-000000000003','INTERIOR','SUBASSEMBLY','Complete seat intended for a motor vehicle.'),
    ('63100000-0000-4000-8000-000000000004','SUBASM-LAMINATED-WINDSHIELD','夹层前挡玻璃分总成','Laminated windshield subassembly','62100000-0000-4000-8000-000000000004','VISIBILITY_LIGHTING','SUBASSEMBLY','Laminated safety glass shaped for a vehicle.'),
    ('63100000-0000-4000-8000-000000000005','SUBASM-VEHICLE-LAMP','机动车灯具分总成','Motor-vehicle lamp subassembly','62100000-0000-4000-8000-000000000005','VISIBILITY_LIGHTING','SUBASSEMBLY','Lighting or visual signalling equipment.'),
    ('63100000-0000-4000-8000-000000000006','SUBASM-AC-COMPRESSOR','空调压缩机分总成','A/C compressor subassembly','62100000-0000-4000-8000-000000000006','THERMAL_MANAGEMENT','SUBASSEMBLY','Refrigerant compressor for vehicle climate control.'),
    ('63100000-0000-4000-8000-000000000007','SUBASM-DRIVE-AXLE-DIFFERENTIAL','驱动桥差速器分总成','Drive axle and differential subassembly','62100000-0000-4000-8000-000000000007','DRIVELINE','SUBASSEMBLY','Drive axle with differential, with or without transmission elements.'),
    ('63100000-0000-4000-8000-000000000008','SUBASM-BUMPER','保险杠分总成','Bumper subassembly','62100000-0000-4000-8000-000000000008','BODY','SUBASSEMBLY','Bumper assembly or separately presented bumper part.'),
    ('63100000-0000-4000-8000-000000000009','SUBASM-SAFETY-SEAT-BELT','安全带分总成','Safety seat-belt subassembly','62100000-0000-4000-8000-000000000009','OCCUPANT_SAFETY','SUBASSEMBLY','Seat-belt webbing, retractor, buckle and anchorage hardware.'),
    ('63100000-0000-4000-8000-000000000010','SUBASM-VEHICLE-RADIATOR','机动车散热器分总成','Motor-vehicle radiator subassembly','62100000-0000-4000-8000-000000000010','THERMAL_MANAGEMENT','SUBASSEMBLY','Complete radiator or separately presented radiator part.')
)
INSERT INTO customs.customs_classification_unit (
  ccu_id, ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id,
  vehicle_system, unit_level, function_description, technical_qualifiers,
  assembly_state, included_items, excluded_items, required_input_fields,
  gri_2a_risk, version, record_status, verification_status
)
SELECT ccu_id, ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id,
       vehicle_system, unit_level::ref.ccu_unit_level, function_description, '{}'::jsonb,
       'UNKNOWN'::ref.assembly_state, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
       CASE WHEN unit_level = 'CUSTOMS_CLASSIFICATION_UNIT' THEN 'MEDIUM'::ref.risk_level ELSE 'LOW'::ref.risk_level END,
       1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
FROM rows
ON CONFLICT DO NOTHING;

WITH leaves (
  ccu_id, ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id,
  vehicle_system, function_description, material_spec, required_input_fields
) AS (
  VALUES
    ('64100000-0000-4000-8000-000000000001'::uuid,'CCU-VEHICLE-WIRING-HARNESS','机动车线束','Motor-vehicle wiring harness','63100000-0000-4000-8000-000000000001'::uuid,'VEHICLE_ELECTRICAL','Distributes power or signals through assembled insulated conductors.','Insulated conductors, terminals, connectors and protective coverings.','["vehicle.intended_heading","part.voltage_v","part.conductor_count","part.insulation_material","part.harness_function","shipment.assembly_state"]'::jsonb),
    ('64100000-0000-4000-8000-000000000002','CCU-SAFETY-AIRBAG','安全气囊模块或部件','Safety airbag module or part','63100000-0000-4000-8000-000000000002','OCCUPANT_SAFETY','Provides inflatable occupant restraint.','Airbag cushion, inflator and housing according to presentation.','["part.presentation_scope","part.includes_inflator","part.includes_cushion","vehicle.intended_heading","shipment.assembly_state"]'),
    ('64100000-0000-4000-8000-000000000003','CCU-MOTOR-VEHICLE-SEAT','机动车座椅','Motor-vehicle seat','63100000-0000-4000-8000-000000000003','INTERIOR','Seats a vehicle occupant.','Seat frame, cushion, trim and integrated mechanisms according to presentation.','["vehicle.intended_heading","part.complete_seat","part.integrated_airbag","part.integrated_heating","shipment.assembly_state"]'),
    ('64100000-0000-4000-8000-000000000004','CCU-LAMINATED-WINDSHIELD','机动车夹层前挡玻璃','Motor-vehicle laminated windshield','63100000-0000-4000-8000-000000000004','VISIBILITY_LIGHTING','Provides forward visibility and occupant protection.','Laminated safety glass cut and shaped for installation.','["part.glass_construction","part.shaped_for_vehicle","vehicle.intended_heading","part.integrated_electronics","shipment.assembly_state"]'),
    ('64100000-0000-4000-8000-000000000005','CCU-VEHICLE-LIGHTING-SIGNALLING','机动车照明或视觉信号装置','Motor-vehicle lighting or visual signalling equipment','63100000-0000-4000-8000-000000000005','VISIBILITY_LIGHTING','Illuminates the road or communicates visual signals.','Lamp housing, optical unit and light source/control electronics according to presentation.','["part.lamp_function","part.assembled_state","vehicle.type","part.integrated_control_module","shipment.assembly_state"]'),
    ('64100000-0000-4000-8000-000000000006','CCU-VEHICLE-AC-COMPRESSOR','机动车空调压缩机','Motor-vehicle A/C compressor','63100000-0000-4000-8000-000000000006','THERMAL_MANAGEMENT','Compresses refrigerant for vehicle climate control.','Mechanical or electrically driven refrigerant compressor.','["part.refrigeration_capacity_kw","part.displacement_cc_per_rev","part.drive_type","part.integrated_motor","shipment.assembly_state"]'),
    ('64100000-0000-4000-8000-000000000007','CCU-DRIVE-AXLE-DIFFERENTIAL','驱动桥及差速器','Drive axle with differential','63100000-0000-4000-8000-000000000007','DRIVELINE','Transfers and divides torque to driven wheels.','Drive axle, differential and transmission components according to presentation.','["vehicle.intended_heading","part.presentation_scope","part.driving_axle","part.integrated_transmission_components","shipment.assembly_state"]'),
    ('64100000-0000-4000-8000-000000000008','CCU-VEHICLE-BUMPER','机动车保险杠或部件','Motor-vehicle bumper or part','63100000-0000-4000-8000-000000000008','BODY','Absorbs or manages low-speed exterior impacts.','Bumper beam, absorber, cover and brackets according to presentation.','["vehicle.intended_heading","part.presentation_scope","part.material","part.includes_cover","shipment.assembly_state"]'),
    ('64100000-0000-4000-8000-000000000009','CCU-SAFETY-SEAT-BELT','机动车安全带','Motor-vehicle safety seat belt','63100000-0000-4000-8000-000000000009','OCCUPANT_SAFETY','Restrains an occupant during vehicle movement or collision.','Webbing with buckle, retractor and anchorage hardware according to presentation.','["part.complete_belt","part.includes_retractor","part.includes_pretensioner","vehicle.intended_heading","shipment.assembly_state"]'),
    ('64100000-0000-4000-8000-000000000010','CCU-VEHICLE-RADIATOR','机动车散热器或部件','Motor-vehicle radiator or part','63100000-0000-4000-8000-000000000010','THERMAL_MANAGEMENT','Transfers coolant heat to ambient air.','Radiator core, tanks, fittings and frame according to presentation.','["vehicle.intended_heading","part.presentation_scope","part.cooling_medium","part.integrated_fan","shipment.assembly_state"]')
)
INSERT INTO customs.customs_classification_unit (
  ccu_id, ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id,
  vehicle_system, unit_level, function_description, material_spec,
  technical_qualifiers, assembly_state, included_items, excluded_items,
  required_input_fields, gri_2a_risk, version, record_status,
  verification_status
)
SELECT ccu_id, ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id,
       vehicle_system, 'CUSTOMS_CLASSIFICATION_UNIT'::ref.ccu_unit_level, function_description,
       material_spec, '{}'::jsonb, 'UNKNOWN'::ref.assembly_state, '[]'::jsonb, '[]'::jsonb,
       required_input_fields, 'MEDIUM'::ref.risk_level, 1,
       'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
FROM leaves
ON CONFLICT DO NOTHING;

WITH candidates (candidate_id, ccu_id, candidate_rank, hs6_code, basis, exclusions) AS (
  VALUES
    ('65100000-0000-4000-8000-000000000011'::uuid,'64100000-0000-4000-8000-000000000001'::uuid,1,'854430','Ignition wiring sets and other wiring sets used in vehicles.','National branch requires technical and parent-indentation facts.'),
    ('65100000-0000-4000-8000-000000000021','64100000-0000-4000-8000-000000000002',1,'870895','Safety airbags with inflator systems and parts thereof.','Separate sensors and control units require specific-heading review.'),
    ('65100000-0000-4000-8000-000000000031','64100000-0000-4000-8000-000000000003',1,'940120','Seats of a kind used for motor vehicles.','Seat parts and child seats require separate review.'),
    ('65100000-0000-4000-8000-000000000041','64100000-0000-4000-8000-000000000004',1,'700721','Laminated safety glass shaped for vehicles.','Tempered glass and unshaped glass are excluded.'),
    ('65100000-0000-4000-8000-000000000051','64100000-0000-4000-8000-000000000005',1,'851220','Other vehicle lighting or visual signalling equipment.','Electrical control units and general lamps require review.'),
    ('65100000-0000-4000-8000-000000000061','64100000-0000-4000-8000-000000000006',1,'841430','Compressors used in refrigerating equipment.','Confirm compressor function and capacity; integrated assemblies may differ.'),
    ('65100000-0000-4000-8000-000000000071','64100000-0000-4000-8000-000000000007',1,'870850','Drive axles with differential and parts thereof.','Exact presentation and PDK parent branch are required.'),
    ('65100000-0000-4000-8000-000000000081','64100000-0000-4000-8000-000000000008',1,'870810','Bumpers and parts thereof.','Material-specific articles not identifiable as bumper parts require review.'),
    ('65100000-0000-4000-8000-000000000091','64100000-0000-4000-8000-000000000009',1,'870821','Safety seat belts.','Loose textile webbing and separate electrical pretensioner items require review.'),
    ('65100000-0000-4000-8000-000000000101','64100000-0000-4000-8000-000000000010',1,'870891','Radiators and parts thereof.','General heat exchangers and battery-only chillers require specific-heading review.')
)
INSERT INTO customs.ccu_candidate_hs (
  candidate_id, ccu_id, candidate_rank, hs_nomenclature_version,
  hs6_code, candidate_basis, exclusion_notes, verification_status
)
SELECT candidate_id, ccu_id, candidate_rank, 'HS-2022', hs6_code,
       basis, exclusions, 'CANDIDATE'::ref.verification_status
FROM candidates
ON CONFLICT DO NOTHING;

INSERT INTO customs.ccu_risk_tag (
  ccu_risk_tag_id, ccu_id, risk_tag_type, risk_level,
  trigger_condition, risk_note, verification_status
)
SELECT gen_random_uuid(), c.ccu_id, tag.risk_tag_type,
       CASE WHEN tag.risk_tag_type = 'HEADING_8708_EXCLUSION' THEN 'MEDIUM'::ref.risk_level
            ELSE 'MEDIUM'::ref.risk_level END,
       CASE tag.risk_tag_type
         WHEN 'GRI_2A' THEN '{"field":"shipment.assembly_state","operator":"NE","value":"COMPLETE"}'::jsonb
         WHEN 'HEADING_8708_EXCLUSION' THEN '{"field":"classification.specific_heading_review_completed","operator":"EQ","value":false}'::jsonb
         ELSE '{"field":"scenario.import_mode","operator":"IN","value":["CKD","SKD"]}'::jsonb
       END,
       CASE tag.risk_tag_type
         WHEN 'GRI_2A' THEN 'Review incomplete, unassembled or disassembled presentation under GRI 2(a).'
         WHEN 'HEADING_8708_EXCLUSION' THEN 'Review Section XVII notes and more specific headings before using heading 8708.'
         ELSE 'Portal tariff-line observation does not replace vehicle-programme AP and import-control review.'
       END,
       'CANDIDATE'
FROM customs.customs_classification_unit c
CROSS JOIN (
  VALUES ('GRI_2A'::ref.risk_tag_type),
         ('HEADING_8708_EXCLUSION'::ref.risk_tag_type),
         ('AP_REGULATORY'::ref.risk_tag_type)
) tag(risk_tag_type)
WHERE c.ccu_id::text LIKE '64100000-%'
  AND NOT EXISTS (
    SELECT 1 FROM customs.ccu_risk_tag existing
    WHERE existing.ccu_id = c.ccu_id
      AND existing.risk_tag_type = tag.risk_tag_type
  );

COMMIT;
