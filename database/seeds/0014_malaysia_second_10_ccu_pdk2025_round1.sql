BEGIN;

WITH docs (source_code, hs6, sha256) AS (
  VALUES
    ('SRC-MY-JKDM-PDK2025-854430-20260729','854430','32a33c3de2fad0e26df2fdc4c3eaa5998adeef29335c7b3e2aab3ecd79732db9'),
    ('SRC-MY-JKDM-PDK2025-870895-20260729','870895','07a2e8805d5b4ce9ea1e4940fffc1ba11c76080c2c553ddc22c58582efe77ba9'),
    ('SRC-MY-JKDM-PDK2025-940120-20260729','940120','0a9cd641d8ac703487a000a3447867a075cfb14d70b5b38393300d040663d960'),
    ('SRC-MY-JKDM-PDK2025-700721-20260729','700721','cf6131bd845df7768c282f402ab8dd18d5dad92b96a570996d4cb35f760cc71e'),
    ('SRC-MY-JKDM-PDK2025-851220-20260729','851220','86b3e9975089b4e42faf95b9f37daea7f5f76d7a4f8037e0a33336726c72bb1f'),
    ('SRC-MY-JKDM-PDK2025-841430-20260729','841430','8487949ec15047c38c80654f0f6d5bc77c3843315272e6a9222ec17cc2ff454c'),
    ('SRC-MY-JKDM-PDK2025-870850-20260729','870850','a278308e7c837ad075324e562ba67b97e156b986a80b41ef9631f1d2c45de328'),
    ('SRC-MY-JKDM-PDK2025-870810-20260729','870810','6e029864acaaf51ffe5ad2e41cc215ffa7173653383912c6e0457a7edc583361'),
    ('SRC-MY-JKDM-PDK2025-870821-20260729','870821','17c433bf692eaf5bde6a9ec95d568ab502e124dd006c89500333777c644414a0'),
    ('SRC-MY-JKDM-PDK2025-870891-20260729','870891','cc550ccae2e0321d3595dbdaf374f90af2645698f659c48faeb55d180d03d5c9')
)
INSERT INTO evidence.source_document (
  source_code, authority_id, document_title, source_type, official_status,
  canonical_url, effective_from, accessed_at, language_code, content_sha256,
  archived_object_key, version, record_status
)
SELECT source_code,
       (SELECT authority_id FROM ref.authority WHERE authority_code='MY-JKDM'),
       'JKDM HS Explorer PDK 2025 result - HS ' || hs6,
       'OFFICIAL_PORTAL','OFFICIAL',
       'https://ezhs.customs.gov.my/public-find-hs-data',
       DATE '2025-11-01', TIMESTAMPTZ '2026-07-29 12:00:00+08','en',
       sha256, 'evidence/my/2026-07-29/JKDM_HS_Explorer_PDK2025_' || hs6 || '.html',
       1,'ACTIVE'
FROM docs
ON CONFLICT (source_code) DO UPDATE
SET content_sha256=EXCLUDED.content_sha256,
    archived_object_key=EXCLUDED.archived_object_key,
    accessed_at=EXCLUDED.accessed_at,
    record_status='ACTIVE';

WITH clauses (clause_code, source_code, hs6, summary) AS (
  VALUES
    ('CLAUSE-MY-PDK2025-854430-ROUND1','SRC-MY-JKDM-PDK2025-854430-20260729','854430','PDK 2025 lines retained: 8544301200 at 30% duty and 8544301400 at 5%; both display SST 10%. Parent indentation and technical facts remain unresolved.'),
    ('CLAUSE-MY-PDK2025-870895-ROUND1','SRC-MY-JKDM-PDK2025-870895-20260729','870895','8708951000 complete safety airbags and 8708959000 parts; duty 30%, displayed SST 10%.'),
    ('CLAUSE-MY-PDK2025-940120-ROUND1','SRC-MY-JKDM-PDK2025-940120-20260729','940120','9401201000 seats for vehicles of headings 8702, 8703 or 8704; duty 30%, displayed SST 10%.'),
    ('CLAUSE-MY-PDK2025-700721-ROUND1','SRC-MY-JKDM-PDK2025-700721-20260729','700721','7007211000 laminated safety glass suitable for vehicles of Chapter 87; duty 30%, displayed SST 10%.'),
    ('CLAUSE-MY-PDK2025-851220-ROUND1','SRC-MY-JKDM-PDK2025-851220-20260729','851220','8512202000 unassembled equipment and 8512209900 other non-motorcycle equipment; duty 0%, displayed SST 10%.'),
    ('CLAUSE-MY-PDK2025-841430-ROUND1','SRC-MY-JKDM-PDK2025-841430-20260729','841430','8414304000 high-capacity/displacement compressors and 8414309000 other; duty 0%, displayed SST 5%.'),
    ('CLAUSE-MY-PDK2025-870850-ROUND1','SRC-MY-JKDM-PDK2025-870850-20260729','870850','Passenger-vehicle drive-axle candidates 8708501100 and 8708502600; duty 25%, displayed SST 10%; parent indentation unresolved.'),
    ('CLAUSE-MY-PDK2025-870810-ROUND1','SRC-MY-JKDM-PDK2025-870810-20260729','870810','8708109000 other bumpers and parts; duty 25%, displayed SST 10%.'),
    ('CLAUSE-MY-PDK2025-870821-ROUND1','SRC-MY-JKDM-PDK2025-870821-20260729','870821','8708210000 safety seat belts; duty 30%, displayed SST 10%.'),
    ('CLAUSE-MY-PDK2025-870891-ROUND1','SRC-MY-JKDM-PDK2025-870891-20260729','870891','Passenger-vehicle radiator candidates 8708911600 and 8708919500; duty 25%, displayed SST 10%; complete/parts parent indentation requires confirmation.')
)
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary, extraction_method,
  extracted_at, verification_status
)
SELECT c.clause_code, d.source_document_id, 'PORTAL_QUERY',
       'POST hsType=PDK; hsCriteria=1; hsKeyword=' || c.hs6 || '; find_item=yes',
       c.summary, c.summary, c.summary, 'MANUAL_VERIFIED_EXTRACTION',
       TIMESTAMPTZ '2026-07-29 12:30:00+08','VERIFIED'
FROM clauses c
JOIN evidence.source_document d ON d.source_code=c.source_code
ON CONFLICT (clause_code) DO UPDATE
SET original_text=EXCLUDED.original_text,
    translated_text_cn=EXCLUDED.translated_text_cn,
    evidence_summary=EXCLUDED.evidence_summary,
    extracted_at=EXCLUDED.extracted_at,
    verification_status='VERIFIED';

WITH mappings (
  mapping_code, candidate_id, national_code, description, duty, sst,
  status, condition, control_hash
) AS (
  VALUES
    ('MAP-MY-PDK2025-MFN-8544301200','65100000-0000-4000-8000-000000000011'::uuid,'8544301200','Of a kind used for vehicles of heading 87.02, 87.03, 87.04 or 87.11',0.30,0.10,'CANDIDATE','{"requires":["vehicle.intended_heading","part.voltage_v","part.conductor_count","part.insulation_material","part.harness_function"]}'::jsonb,'5496cd009a7d5dee1a9fb8704c8d7c37061266cf7d7f5a792b20ea630b736681'),
    ('MAP-MY-PDK2025-MFN-8544301400','65100000-0000-4000-8000-000000000011','8544301400','Of a kind used for vehicles of heading 87.02, 87.03, 87.04 or 87.11',0.05,0.10,'CANDIDATE','{"requires":["vehicle.intended_heading","part.voltage_v","part.conductor_count","part.insulation_material","part.harness_function"]}','170a33459b61d34f9aca72c8dcf278adb5171047f2d7bf003787329095797980'),
    ('MAP-MY-PDK2025-MFN-8708951000','65100000-0000-4000-8000-000000000021','8708951000','Safety airbags with inflater system',0.30,0.10,'VERIFIED','{"part.presentation_scope":"COMPLETE_AIRBAG_WITH_INFLATOR"}','30e418f8661938d2e68b9e5c46bc58a311ebeac15cc70ec79ff65ed4e55bce19'),
    ('MAP-MY-PDK2025-MFN-8708959000','65100000-0000-4000-8000-000000000021','8708959000','Parts of safety airbags',0.30,0.10,'CANDIDATE','{"part.presentation_scope":"AIRBAG_PART"}','cb32bd3987f58a7877cada2dea8066a84b8781ac00a6b92c296356e2f5402dba'),
    ('MAP-MY-PDK2025-MFN-9401201000','65100000-0000-4000-8000-000000000031','9401201000','Of a kind used for vehicles of heading 87.02, 87.03 or 87.04',0.30,0.10,'VERIFIED','{"vehicle.intended_heading":["8702","8703","8704"],"part.complete_seat":true}','65f1f1351a1440e644faa6bd3b593b915a4be4d585a6e9883c1142d6c7261694'),
    ('MAP-MY-PDK2025-MFN-7007211000','65100000-0000-4000-8000-000000000041','7007211000','Suitable for vehicles of Chapter 87',0.30,0.10,'VERIFIED','{"part.glass_construction":"LAMINATED","part.shaped_for_vehicle":true}','24a3c804edd5e4ac4d3ecf852d62c85116cb1c827a038c4b4449bcacf8ddd84d'),
    ('MAP-MY-PDK2025-MFN-8512202000','65100000-0000-4000-8000-000000000051','8512202000','Unassembled lighting or visual signalling equipment',0.00,0.10,'CANDIDATE','{"part.assembled_state":"UNASSEMBLED"}','5496cd009a7d5dee1a9fb8704c8d7c37061266cf7d7f5a792b20ea630b736681'),
    ('MAP-MY-PDK2025-MFN-8512209900','65100000-0000-4000-8000-000000000051','8512209900','Other lighting or visual signalling equipment',0.00,0.10,'CANDIDATE','{"vehicle.type":{"not":"MOTORCYCLE"},"part.assembled_state":"ASSEMBLED"}','170a33459b61d34f9aca72c8dcf278adb5171047f2d7bf003787329095797980'),
    ('MAP-MY-PDK2025-MFN-8414304000','65100000-0000-4000-8000-000000000061','8414304000','Refrigeration capacity exceeding 21.10 kW or displacement at least 220 cc/rev',0.00,0.05,'CANDIDATE','{"any":[{"part.refrigeration_capacity_kw":{"gt":21.10}},{"part.displacement_cc_per_rev":{"gte":220}}]}','5534a01426b11ed98e89e5e3714194f3afab47d948c9fa4379eee20b1630888a'),
    ('MAP-MY-PDK2025-MFN-8414309000','65100000-0000-4000-8000-000000000061','8414309000','Other refrigerating compressors',0.00,0.05,'CANDIDATE','{"requires":["part.refrigeration_capacity_kw","part.displacement_cc_per_rev"]}','9c14ee57f2773ccd1bfe904ce9e78c4726bf34af2f5abc73d719cb977c761a79'),
    ('MAP-MY-PDK2025-MFN-8708501100','65100000-0000-4000-8000-000000000071','8708501100','For vehicles of heading 87.03',0.25,0.10,'CANDIDATE','{"vehicle.intended_heading":"8703","requires":["part.presentation_scope","part.driving_axle"]}','30e418f8661938d2e68b9e5c46bc58a311ebeac15cc70ec79ff65ed4e55bce19'),
    ('MAP-MY-PDK2025-MFN-8708502600','65100000-0000-4000-8000-000000000071','8708502600','For vehicles of heading 87.03',0.25,0.10,'CANDIDATE','{"vehicle.intended_heading":"8703","requires":["part.presentation_scope","part.driving_axle"]}','8646b8cd389cc44447ad67b7ad05a8527aa04ebf418b7795dca1830a4afcacab'),
    ('MAP-MY-PDK2025-MFN-8708109000','65100000-0000-4000-8000-000000000081','8708109000','Other bumpers and parts thereof',0.25,0.10,'VERIFIED','{"vehicle.intended_heading":{"not":"8701"}}','cb32bd3987f58a7877cada2dea8066a84b8781ac00a6b92c296356e2f5402dba'),
    ('MAP-MY-PDK2025-MFN-8708210000','65100000-0000-4000-8000-000000000091','8708210000','Safety seat belts',0.30,0.10,'VERIFIED','{"part.complete_belt":true}','7b9b7ed389d1d4e2a97e1e717d974d97d431bf0ef5a83620b1f2d6a53ebcbd9f'),
    ('MAP-MY-PDK2025-MFN-8708911600','65100000-0000-4000-8000-000000000101','8708911600','Radiators for vehicles of heading 87.03',0.25,0.10,'CANDIDATE','{"vehicle.intended_heading":"8703","part.presentation_scope":"COMPLETE_RADIATOR"}','cb32bd3987f58a7877cada2dea8066a84b8781ac00a6b92c296356e2f5402dba'),
    ('MAP-MY-PDK2025-MFN-8708919500','65100000-0000-4000-8000-000000000101','8708919500','Other radiator parts for vehicles of heading 87.03',0.25,0.10,'CANDIDATE','{"vehicle.intended_heading":"8703","part.presentation_scope":"RADIATOR_PART"}','f77b9fa815e6b8cfa58e5238ca23958e40c1c7687e5c6606745ad20171c1fbf9')
),
prepared AS (
  SELECT m.*,
         c.hs6_code,
         sc.source_clause_id
  FROM mappings m
  JOIN customs.ccu_candidate_hs c ON c.candidate_id=m.candidate_id
  JOIN evidence.source_clause sc
    ON sc.clause_code='CLAUSE-MY-PDK2025-' || c.hs6_code || '-ROUND1'
)
INSERT INTO customs.tariff_mapping (
  mapping_code, country_id, candidate_id, tariff_version,
  national_tariff_code, tariff_description, origin_regime,
  duty_rate, rate_type, additional_measure, eligibility_condition,
  effective_from, version, source_clause_id, record_status,
  verification_status
)
SELECT mapping_code,
       (SELECT country_id FROM ref.country WHERE iso2='MY'),
       candidate_id, 'PDK 2025', national_code, description, 'MFN',
       duty, CASE WHEN duty=0 THEN 'ZERO'::ref.rate_type ELSE 'AD_VALOREM'::ref.rate_type END,
       jsonb_build_object(
         'sst',jsonb_build_object('displayed_rate',sst,'portal_display_verified',true),
         'portal_import_control',jsonb_build_object(
           'result','NO_DATA_DISPLAYED','observed_on','2026-07-29',
           'legal_conclusion',false,'content_sha256',control_hash,
           'archived_object_key','evidence/my/2026-07-29/JKDM_HS_Explorer_Import_Control_' || national_code || '.html'
         )
       ),
       condition, DATE '2025-11-01',1,source_clause_id,'ACTIVE',
       status::ref.verification_status
FROM prepared
ON CONFLICT (mapping_code,version) DO UPDATE
SET national_tariff_code=EXCLUDED.national_tariff_code,
    tariff_description=EXCLUDED.tariff_description,
    duty_rate=EXCLUDED.duty_rate,
    rate_type=EXCLUDED.rate_type,
    additional_measure=EXCLUDED.additional_measure,
    eligibility_condition=EXCLUDED.eligibility_condition,
    source_clause_id=EXCLUDED.source_clause_id,
    record_status='ACTIVE',
    verification_status=EXCLUDED.verification_status,
    updated_at=now();

COMMIT;
