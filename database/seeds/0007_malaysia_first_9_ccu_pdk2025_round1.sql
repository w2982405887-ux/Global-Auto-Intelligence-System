BEGIN;

-- Malaysia PDK 2025 round-one mapping for the nine CCUs added by seed 0006.
--
-- Evidence scope:
--   * JKDM HS Explorer PDK 2025 result pages for national tariff code,
--     MFN import duty and the SST rate displayed by the portal.
--   * JKDM HS Explorer prohibition-detail responses for each retained
--     national tariff candidate.
--
-- Classification scope:
--   * A VERIFIED mapping means the generic CCU definition and the stated
--     eligibility condition are sufficient for this national line.
--   * A CANDIDATE mapping keeps a real PDK 2025 line and verified rate, but
--     final selection still needs enterprise technical facts, the omitted
--     national indentation label, or an authority/ruling confirmation.
--   * Portal "No Data" is recorded only as an observed portal result. It is
--     not a legal conclusion that no other product or programme control exists.

-- ---------------------------------------------------------------------------
-- 1. Archived official portal responses
-- ---------------------------------------------------------------------------

WITH document_rows (
  source_code, document_title, canonical_url, effective_from,
  content_sha256, archived_object_key
) AS (
  VALUES
    ('SRC-MY-JKDM-PDK2025-850152-20260728',
     'JKDM HS Explorer PDK 2025 result - HS 850152',
     'https://ezhs.customs.gov.my/public-find-hs-data', DATE '2025-11-01',
     '63535706b5a0aedca899da9d14be0e48f06f92927f73812e42e93e63609697bc',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_PDK2025_850152.html'),
    ('SRC-MY-JKDM-PDK2025-850153-20260728',
     'JKDM HS Explorer PDK 2025 result - HS 850153',
     'https://ezhs.customs.gov.my/public-find-hs-data', DATE '2025-11-01',
     'f105985bb48846f101621e515f167d35de66c1700c16bf39c086f07f36f17d66',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_PDK2025_850153.html'),
    ('SRC-MY-JKDM-PDK2025-850440-20260728',
     'JKDM HS Explorer PDK 2025 result - HS 850440',
     'https://ezhs.customs.gov.my/public-find-hs-data', DATE '2025-11-01',
     '44fc307e4e5aefa7743dc6bd0e81d5b2686e029c1fb21b3959201f93cd49088c',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_PDK2025_850440.html'),
    ('SRC-MY-JKDM-PDK2025-870710-20260728',
     'JKDM HS Explorer PDK 2025 result - HS 870710',
     'https://ezhs.customs.gov.my/public-find-hs-data', DATE '2025-11-01',
     'aec3eac746770c9ac56a1a9b3adfd08fae0ba69a27454f044caf9dcb606c0ae7',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_PDK2025_870710.html'),
    ('SRC-MY-JKDM-PDK2025-870830-20260728',
     'JKDM HS Explorer PDK 2025 result - HS 870830',
     'https://ezhs.customs.gov.my/public-find-hs-data', DATE '2025-11-01',
     '58ca2e9cb03b03d7ba746c07d35dd791f86cb950320abb43c03546d5c25b7ae7',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_PDK2025_870830.html'),
    ('SRC-MY-JKDM-PDK2025-870870-20260728',
     'JKDM HS Explorer PDK 2025 result - HS 870870',
     'https://ezhs.customs.gov.my/public-find-hs-data', DATE '2025-11-01',
     'd8d008469b6786e23b50a50094a442b4900b338d0967b27e74c43a8ac2a789a0',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_PDK2025_870870.html'),
    ('SRC-MY-JKDM-PDK2025-870880-20260728',
     'JKDM HS Explorer PDK 2025 result - HS 870880',
     'https://ezhs.customs.gov.my/public-find-hs-data', DATE '2025-11-01',
     'fb064b0ee311e5dd9aa1f4c121940351b6640c0e7e0b12b41b6d0a2655f5bedc',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_PDK2025_870880.html'),
    ('SRC-MY-JKDM-PDK2025-870894-20260728',
     'JKDM HS Explorer PDK 2025 result - HS 870894',
     'https://ezhs.customs.gov.my/public-find-hs-data', DATE '2025-11-01',
     '4184d9e80225a54c7701f55a29d151e56a069d9118d79220b585f3e2f0e99fc5',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_PDK2025_870894.html'),

    ('SRC-MY-JKDM-CONTROL-8501521200-20260728',
     'JKDM HS Explorer import-control result - 8501521200',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '2f09d3787df88129f91f3dcf0d65805198d215ab7821dde5bf19085a3d5282f9',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8501521200.html'),
    ('SRC-MY-JKDM-CONTROL-8501522200-20260728',
     'JKDM HS Explorer import-control result - 8501522200',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '2f09d3787df88129f91f3dcf0d65805198d215ab7821dde5bf19085a3d5282f9',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8501522200.html'),
    ('SRC-MY-JKDM-CONTROL-8501523200-20260728',
     'JKDM HS Explorer import-control result - 8501523200',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '2f09d3787df88129f91f3dcf0d65805198d215ab7821dde5bf19085a3d5282f9',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8501523200.html'),
    ('SRC-MY-JKDM-CONTROL-8501531000-20260728',
     'JKDM HS Explorer import-control result - 8501531000',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '2f09d3787df88129f91f3dcf0d65805198d215ab7821dde5bf19085a3d5282f9',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8501531000.html'),
    ('SRC-MY-JKDM-CONTROL-8504402000-20260728',
     'JKDM HS Explorer import-control result - 8504402000',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '22eccdfa67cbd193aff3a74a00986a8b2dbdcb5da42c23e2a9c4cc23edcd78fc',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8504402000.html'),
    ('SRC-MY-JKDM-CONTROL-8504403000-20260728',
     'JKDM HS Explorer import-control result - 8504403000',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '22eccdfa67cbd193aff3a74a00986a8b2dbdcb5da42c23e2a9c4cc23edcd78fc',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8504403000.html'),
    ('SRC-MY-JKDM-CONTROL-8504404000-20260728',
     'JKDM HS Explorer import-control result - 8504404000',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '22eccdfa67cbd193aff3a74a00986a8b2dbdcb5da42c23e2a9c4cc23edcd78fc',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8504404000.html'),
    ('SRC-MY-JKDM-CONTROL-8504409000-20260728',
     'JKDM HS Explorer import-control result - 8504409000',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     'c2b58fb6996cf318f33da56881e6a5a74bebb6f36aa8231c3fefcaecf21f6529',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8504409000.html'),
    ('SRC-MY-JKDM-CONTROL-8707109000-20260728',
     'JKDM HS Explorer import-control result - 8707109000',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '067c632e2f91a896eefc560694d4000e2da2214d09379c3b5663a2b420d29b7e',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8707109000.html'),
    ('SRC-MY-JKDM-CONTROL-8708302100-20260728',
     'JKDM HS Explorer import-control result - 8708302100',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '438d1e02bb131141d3b126882e0bc2b8a5da216932ca1fbafc4e9e207db6ef21',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8708302100.html'),
    ('SRC-MY-JKDM-CONTROL-8708302900-20260728',
     'JKDM HS Explorer import-control result - 8708302900',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '2d00ccef8d213e11a0d2c84df5e0488fd2514dfc1b3f1af516e0ad86b892a227',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8708302900.html'),
    ('SRC-MY-JKDM-CONTROL-8708701600-20260728',
     'JKDM HS Explorer import-control result - 8708701600',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '438d1e02bb131141d3b126882e0bc2b8a5da216932ca1fbafc4e9e207db6ef21',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8708701600.html'),
    ('SRC-MY-JKDM-CONTROL-8708702200-20260728',
     'JKDM HS Explorer import-control result - 8708702200',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '438d1e02bb131141d3b126882e0bc2b8a5da216932ca1fbafc4e9e207db6ef21',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8708702200.html'),
    ('SRC-MY-JKDM-CONTROL-8708703200-20260728',
     'JKDM HS Explorer import-control result - 8708703200',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '438d1e02bb131141d3b126882e0bc2b8a5da216932ca1fbafc4e9e207db6ef21',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8708703200.html'),
    ('SRC-MY-JKDM-CONTROL-8708709700-20260728',
     'JKDM HS Explorer import-control result - 8708709700',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '438d1e02bb131141d3b126882e0bc2b8a5da216932ca1fbafc4e9e207db6ef21',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8708709700.html'),
    ('SRC-MY-JKDM-CONTROL-8708801600-20260728',
     'JKDM HS Explorer import-control result - 8708801600',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '438d1e02bb131141d3b126882e0bc2b8a5da216932ca1fbafc4e9e207db6ef21',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8708801600.html'),
    ('SRC-MY-JKDM-CONTROL-8708809200-20260728',
     'JKDM HS Explorer import-control result - 8708809200',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '438d1e02bb131141d3b126882e0bc2b8a5da216932ca1fbafc4e9e207db6ef21',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8708809200.html'),
    ('SRC-MY-JKDM-CONTROL-8708949500-20260728',
     'JKDM HS Explorer import-control result - 8708949500',
     'https://ezhs.customs.gov.my/public-larangan', NULL,
     '438d1e02bb131141d3b126882e0bc2b8a5da216932ca1fbafc4e9e207db6ef21',
     'evidence/my/2026-07-28/JKDM_HS_Explorer_Import_Control_8708949500.html')
)
INSERT INTO evidence.source_document (
  source_code, authority_id, document_title, source_type, official_status,
  canonical_url, effective_from, accessed_at, language_code,
  content_sha256, archived_object_key, version, record_status
)
SELECT
  d.source_code,
  (SELECT authority_id FROM ref.authority WHERE authority_code = 'MY-JKDM'),
  d.document_title, 'OFFICIAL_PORTAL', 'OFFICIAL',
  d.canonical_url, d.effective_from,
  TIMESTAMPTZ '2026-07-28 16:30:00+08', 'en',
  d.content_sha256, d.archived_object_key, 1, 'ACTIVE'
FROM document_rows d
ON CONFLICT (source_code) DO UPDATE
SET document_title = EXCLUDED.document_title,
    canonical_url = EXCLUDED.canonical_url,
    effective_from = EXCLUDED.effective_from,
    accessed_at = EXCLUDED.accessed_at,
    content_sha256 = EXCLUDED.content_sha256,
    archived_object_key = EXCLUDED.archived_object_key,
    record_status = 'ACTIVE';

-- ---------------------------------------------------------------------------
-- 2. Atomic tariff-result clauses
-- ---------------------------------------------------------------------------

WITH clause_rows (
  clause_code, source_code, locator_value, original_text,
  translated_text_cn, evidence_summary
) AS (
  VALUES
    ('CLAUSE-MY-PDK2025-850152-ROUND1',
     'SRC-MY-JKDM-PDK2025-850152-20260728',
     'POST hsType=PDK; hsCriteria=1; hsKeyword=850152; find_item=yes',
     '8501521200, 8501522200 and 8501523200: Of a kind used for vehicles in Chapter 87; import rate 15%; export rate 0%; SST 10%.',
     '8501521200、8501522200和8501523200：用于第87章车辆；进口税率15%，出口税率0%，页面显示SST 10%。',
     'PDK 2025 exposes three vehicle national lines under 850152. The portal result does not expose the omitted parent indentation that distinguishes the 12/22/32 branches.'),
    ('CLAUSE-MY-PDK2025-850153-ROUND1',
     'SRC-MY-JKDM-PDK2025-850153-20260728',
     'POST hsType=PDK; hsCriteria=1; hsKeyword=850153; find_item=yes',
     '8501531000: Of a kind used for vehicles in Chapter 87; import rate 0%; export rate 0%; SST 10%.',
     '8501531000：用于第87章车辆；进口税率0%，出口税率0%，页面显示SST 10%。',
     'PDK 2025 vehicle line for a multi-phase AC motor of output exceeding 75 kW.'),
    ('CLAUSE-MY-PDK2025-850440-ROUND1',
     'SRC-MY-JKDM-PDK2025-850440-20260728',
     'POST hsType=PDK; hsCriteria=1; hsKeyword=850440; find_item=yes',
     '8504402000 battery chargers having a rating exceeding 100 kVA; 8504403000 other rectifiers; 8504404000 inverters; 8504409000 other. Each displays import rate 0%, export rate 0%, SST 10%.',
     '8504402000为额定容量超过100 kVA的充电器；8504403000为其他整流器；8504404000为逆变器；8504409000为其他。各行进口税率0%，出口税率0%，页面显示SST 10%。',
     'PDK 2025 static-converter lines retained for inverter, on-board charger and DC-DC converter conditional mapping.'),
    ('CLAUSE-MY-PDK2025-870710-ROUND1',
     'SRC-MY-JKDM-PDK2025-870710-20260728',
     'POST hsType=PDK; hsCriteria=1; hsKeyword=870710; find_item=yes',
     '8707109000: Other bodies for vehicles of heading 87.03; import rate 30%; export rate 0%; SST 10%.',
     '8707109000：8703品目车辆的其他车身；进口税率30%，出口税率0%，页面显示SST 10%。',
     'PDK 2025 residual passenger-vehicle body line; final use is subject to GRI 2(a) and presentation review.'),
    ('CLAUSE-MY-PDK2025-870830-ROUND1',
     'SRC-MY-JKDM-PDK2025-870830-20260728',
     'POST hsType=PDK; hsCriteria=1; hsKeyword=870830; find_item=yes',
     '8708302100: Brake drums, brake discs or brake pipes; 8708302900: Other. Each displays import rate 30%, export rate 0%, SST 10%.',
     '8708302100：制动鼓、制动盘或制动管；8708302900：其他。各行进口税率30%，出口税率0%，页面显示SST 10%。',
     'Two PDK 2025 candidates retained because the CCU may be an enumerated brake component or another wheel-end brake assembly.'),
    ('CLAUSE-MY-PDK2025-870870-ROUND1',
     'SRC-MY-JKDM-PDK2025-870870-20260728',
     'POST hsType=PDK; hsCriteria=1; hsKeyword=870870; find_item=yes',
     '8708701600, 8708702200, 8708703200 and 8708709700 each state For vehicles of heading 87.03 and display import rate 30%, export rate 0%, SST 10%.',
     '8708701600、8708702200、8708703200和8708709700均标示用于8703品目车辆；进口税率30%，出口税率0%，页面显示SST 10%。',
     'Four passenger-vehicle branches are visible, but the portal result omits the parent indentation labels that distinguish complete wheels and different parts/accessories.'),
    ('CLAUSE-MY-PDK2025-870880-ROUND1',
     'SRC-MY-JKDM-PDK2025-870880-20260728',
     'POST hsType=PDK; hsCriteria=1; hsKeyword=870880; find_item=yes',
     '8708801600 and 8708809200 each state For vehicles of heading 87.03 and display import rate 30%, export rate 0%, SST 10%.',
     '8708801600和8708809200均标示用于8703品目车辆；进口税率30%，出口税率0%，页面显示SST 10%。',
     'Two passenger-vehicle branches are retained because the portal result omits the parent indentation distinguishing suspension-system and shock-absorber branches.'),
    ('CLAUSE-MY-PDK2025-870894-ROUND1',
     'SRC-MY-JKDM-PDK2025-870894-20260728',
     'POST hsType=PDK; hsCriteria=1; hsKeyword=870894; find_item=yes',
     '8708949500: For vehicles of heading 87.03; import rate 25%; export rate 0%; SST 10%.',
     '8708949500：用于8703品目车辆；进口税率25%，出口税率0%，页面显示SST 10%。',
     'PDK 2025 passenger-vehicle line retained for a steering gear or column assembly, subject to exact component configuration.')
)
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary,
  extraction_method, extracted_at, verification_status
)
SELECT
  c.clause_code, d.source_document_id, 'PORTAL_POST_QUERY',
  c.locator_value, c.original_text, c.translated_text_cn,
  c.evidence_summary, 'OFFICIAL_PORTAL_POST_RESPONSE_ARCHIVED',
  TIMESTAMPTZ '2026-07-28 16:30:00+08', 'VERIFIED'
FROM clause_rows c
JOIN evidence.source_document d ON d.source_code = c.source_code
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
-- 3. Atomic prohibition-detail clauses
-- ---------------------------------------------------------------------------

WITH control_rows (
  tariff_code, portal_result, original_text, evidence_summary
) AS (
  VALUES
    ('8501521200','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28. This does not exclude other product, shipment or CKD-programme controls.'),
    ('8501522200','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28. This does not exclude other product, shipment or CKD-programme controls.'),
    ('8501523200','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28. This does not exclude other product, shipment or CKD-programme controls.'),
    ('8501531000','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28. This does not exclude other product, shipment or CKD-programme controls.'),
    ('8504402000','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8504403000','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8504404000','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8504409000','SCHEDULE_ROWS_DISPLAYED',
     'Schedule 4 Part 2: Charger including portable battery charger and adaptor; import accompanied by a certificate of approval or exemption letter issued by Suruhanjaya Tenaga (or Sarawak equivalent). A second row covers wireless charger/WPT and requires a certificate of approval issued by SIRIM Berhad.',
     'Two conditional control rows are displayed. An automotive on-board charger or DC-DC converter must first be tested against the described domestic-apparatus or wireless/WPT product scope; the tariff code alone is not enough.'),
    ('8707109000','SCHEDULE_ROWS_DISPLAYED',
     'Schedule 2 Part 2: Bodies (including cabs) for motor vehicles falling within headings 87.02, 87.03, 87.04, or 87.08; all countries; issuing Ministry of Investment, Trade and Industry.',
     'The body tariff line displays an MITI import-control row. The portal response leaves OGA Code and Mandatory fields blank, so the controlling legal schedule and exact permit/document must still be confirmed.'),
    ('8708302100','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8708302900','SCHEDULE_ROWS_DISPLAYED',
     'Schedule 4 Part 2: replacement parts of braking system on motor; all countries; brake pad standard condition and either E-Mark with UNR certificate, MS-Mark with MS certificate, or Road Transport Department approval letter.',
     'The displayed control is expressly worded for replacement braking-system parts. Application to OEM parts imported in a KD programme requires intended-use and authority confirmation.'),
    ('8708701600','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8708702200','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8708703200','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8708709700','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8708801600','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8708809200','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.'),
    ('8708949500','NO_DATA',
     'No Data For Import Prohibition Schedule.',
     'The JKDM prohibition-detail response displayed no import-prohibition row for this PDK key on 2026-07-28.')
)
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary,
  extraction_method, extracted_at, verification_status
)
SELECT
  'CLAUSE-MY-CONTROL-' || c.tariff_code || '-ROUND1',
  d.source_document_id, 'PORTAL_POST_QUERY',
  'POST PDK_KEY=' || c.tariff_code || '; aa=1; result=' || c.portal_result,
  c.original_text, NULL, c.evidence_summary,
  'OFFICIAL_PORTAL_POST_RESPONSE_ARCHIVED',
  TIMESTAMPTZ '2026-07-28 16:30:00+08', 'VERIFIED'
FROM control_rows c
JOIN evidence.source_document d
  ON d.source_code =
     'SRC-MY-JKDM-CONTROL-' || c.tariff_code || '-20260728'
ON CONFLICT (clause_code) DO UPDATE
SET source_document_id = EXCLUDED.source_document_id,
    locator_type = EXCLUDED.locator_type,
    locator_value = EXCLUDED.locator_value,
    original_text = EXCLUDED.original_text,
    evidence_summary = EXCLUDED.evidence_summary,
    extraction_method = EXCLUDED.extraction_method,
    extracted_at = EXCLUDED.extracted_at,
    verification_status = 'VERIFIED';

-- Attach the verified HS6 result evidence to the candidate records created by
-- seed 0006. This does not promote the final classification.
UPDATE customs.ccu_candidate_hs h
SET source_clause_id = c.source_clause_id
FROM evidence.source_clause c
WHERE (h.hs6_code = '850152' AND c.clause_code = 'CLAUSE-MY-PDK2025-850152-ROUND1')
   OR (h.hs6_code = '850153' AND c.clause_code = 'CLAUSE-MY-PDK2025-850153-ROUND1')
   OR (h.hs6_code = '850440' AND c.clause_code = 'CLAUSE-MY-PDK2025-850440-ROUND1')
   OR (h.hs6_code = '870710' AND c.clause_code = 'CLAUSE-MY-PDK2025-870710-ROUND1')
   OR (h.hs6_code = '870830' AND c.clause_code = 'CLAUSE-MY-PDK2025-870830-ROUND1')
   OR (h.hs6_code = '870870' AND c.clause_code = 'CLAUSE-MY-PDK2025-870870-ROUND1')
   OR (h.hs6_code = '870880' AND c.clause_code = 'CLAUSE-MY-PDK2025-870880-ROUND1')
   OR (h.hs6_code = '870894' AND c.clause_code = 'CLAUSE-MY-PDK2025-870894-ROUND1');

-- ---------------------------------------------------------------------------
-- 4. Conditional MFN tariff mappings
-- ---------------------------------------------------------------------------

WITH mapping_rows (
  mapping_code, candidate_id, tariff_clause_code, control_clause_code,
  national_tariff_code, tariff_description, duty_rate, unit_code,
  portal_control_status, portal_control_scope, eligibility_condition,
  verification_status
) AS (
  VALUES
    ('MAP-MY-MFN-CCU-TRACTION-MOTOR-8501521200-R1',
     '65000000-0000-4000-8000-000000000021'::uuid,
     'CLAUSE-MY-PDK2025-850152-ROUND1','CLAUSE-MY-CONTROL-8501521200-ROUND1',
     '8501521200','Of a kind used for vehicles in Chapter 87',0.15,'u',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"part.current_type","operator":"EQ","value":"MULTI_PHASE_AC"},{"field":"part.rated_output_kw","operator":"GT","value":0.75},{"field":"part.rated_output_kw","operator":"LTE","value":75},{"field":"pdk.national_subdivision_branch","operator":"EQ","value":"12"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-TRACTION-MOTOR-8501522200-R1',
     '65000000-0000-4000-8000-000000000021'::uuid,
     'CLAUSE-MY-PDK2025-850152-ROUND1','CLAUSE-MY-CONTROL-8501522200-ROUND1',
     '8501522200','Of a kind used for vehicles in Chapter 87',0.15,'u',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"part.current_type","operator":"EQ","value":"MULTI_PHASE_AC"},{"field":"part.rated_output_kw","operator":"GT","value":0.75},{"field":"part.rated_output_kw","operator":"LTE","value":75},{"field":"pdk.national_subdivision_branch","operator":"EQ","value":"22"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-TRACTION-MOTOR-8501523200-R1',
     '65000000-0000-4000-8000-000000000021'::uuid,
     'CLAUSE-MY-PDK2025-850152-ROUND1','CLAUSE-MY-CONTROL-8501523200-ROUND1',
     '8501523200','Of a kind used for vehicles in Chapter 87',0.15,'u',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"part.current_type","operator":"EQ","value":"MULTI_PHASE_AC"},{"field":"part.rated_output_kw","operator":"GT","value":0.75},{"field":"part.rated_output_kw","operator":"LTE","value":75},{"field":"pdk.national_subdivision_branch","operator":"EQ","value":"32"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-TRACTION-MOTOR-8501531000-R1',
     '65000000-0000-4000-8000-000000000022'::uuid,
     'CLAUSE-MY-PDK2025-850153-ROUND1','CLAUSE-MY-CONTROL-8501531000-ROUND1',
     '8501531000','Of a kind used for vehicles in Chapter 87',0.00,'u',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"part.current_type","operator":"EQ","value":"MULTI_PHASE_AC"},{"field":"part.rated_output_kw","operator":"GT","value":75},{"field":"vehicle.chapter","operator":"EQ","value":"87"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),

    ('MAP-MY-MFN-CCU-TRACTION-INVERTER-8504404000-R1',
     '65000000-0000-4000-8000-000000000031'::uuid,
     'CLAUSE-MY-PDK2025-850440-ROUND1','CLAUSE-MY-CONTROL-8504404000-ROUND1',
     '8504404000','Inverters',0.00,'u',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"part.primary_function","operator":"EQ","value":"DC_TO_CONTROLLED_MOTOR_CURRENT"},{"field":"part.integrated_functions_change_classification","operator":"EQ","value":false}]}'::jsonb,
     'VERIFIED'::ref.verification_status),

    ('MAP-MY-MFN-CCU-ONBOARD-CHARGER-8504402000-R1',
     '65000000-0000-4000-8000-000000000041'::uuid,
     'CLAUSE-MY-PDK2025-850440-ROUND1','CLAUSE-MY-CONTROL-8504402000-ROUND1',
     '8504402000','Battery chargers having a rating exceeding 100 kVA',0.00,'u',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"part.primary_function","operator":"EQ","value":"BATTERY_CHARGING"},{"field":"part.rating_kva","operator":"GT","value":100}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-ONBOARD-CHARGER-8504403000-R1',
     '65000000-0000-4000-8000-000000000041'::uuid,
     'CLAUSE-MY-PDK2025-850440-ROUND1','CLAUSE-MY-CONTROL-8504403000-ROUND1',
     '8504403000','Other rectifiers',0.00,'u',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"part.primary_function","operator":"EQ","value":"AC_TO_DC_RECTIFICATION"},{"field":"part.rating_kva","operator":"LTE","value":100},{"field":"classification.rectifier_branch_confirmed","operator":"EQ","value":true}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-ONBOARD-CHARGER-8504409000-R1',
     '65000000-0000-4000-8000-000000000041'::uuid,
     'CLAUSE-MY-PDK2025-850440-ROUND1','CLAUSE-MY-CONTROL-8504409000-ROUND1',
     '8504409000','Other static converters',0.00,'u',
     'SCHEDULE_ROWS_DISPLAYED','DOMESTIC_CHARGER_OR_WIRELESS_WPT_SCOPE_CONFIRMATION_REQUIRED',
     '{"all":[{"field":"part.primary_function","operator":"EQ","value":"BATTERY_CHARGING"},{"field":"classification.other_static_converter_branch_confirmed","operator":"EQ","value":true}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),

    ('MAP-MY-MFN-CCU-DC-DC-CONVERTER-8504409000-R1',
     '65000000-0000-4000-8000-000000000051'::uuid,
     'CLAUSE-MY-PDK2025-850440-ROUND1','CLAUSE-MY-CONTROL-8504409000-ROUND1',
     '8504409000','Other static converters',0.00,'u',
     'SCHEDULE_ROWS_DISPLAYED','CHARGER_SCOPE_NORMALLY_NOT_MATCHED_BUT_INTEGRATED_FUNCTIONS_REQUIRE_REVIEW',
     '{"all":[{"field":"part.primary_function","operator":"EQ","value":"DC_TO_DC_CONVERSION"},{"field":"part.integrated_charger","operator":"EQ","value":false}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),

    ('MAP-MY-MFN-CCU-PASSENGER-BODY-SHELL-8707109000-R1',
     '65000000-0000-4000-8000-000000000061'::uuid,
     'CLAUSE-MY-PDK2025-870710-ROUND1','CLAUSE-MY-CONTROL-8707109000-ROUND1',
     '8707109000','Other bodies for vehicles of heading 87.03',0.30,'u',
     'SCHEDULE_ROWS_DISPLAYED','MITI_BODY_IMPORT_CONTROL_ROW_DISPLAYED',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"classification.gri_2a_complete_vehicle_route","operator":"EQ","value":false},{"field":"body.special_use","operator":"NOT_IN","value":["GO_KART","GOLF_CAR","AMBULANCE","SNOW_VEHICLE"]}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),

    ('MAP-MY-MFN-CCU-ROAD-WHEEL-8708701600-R1',
     '65000000-0000-4000-8000-000000000071'::uuid,
     'CLAUSE-MY-PDK2025-870870-ROUND1','CLAUSE-MY-CONTROL-8708701600-ROUND1',
     '8708701600','For vehicles of heading 87.03',0.30,'kg',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"pdk.national_subdivision_branch","operator":"EQ","value":"16"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-ROAD-WHEEL-8708702200-R1',
     '65000000-0000-4000-8000-000000000071'::uuid,
     'CLAUSE-MY-PDK2025-870870-ROUND1','CLAUSE-MY-CONTROL-8708702200-ROUND1',
     '8708702200','For vehicles of heading 87.03',0.30,'kg',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"pdk.national_subdivision_branch","operator":"EQ","value":"22"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-ROAD-WHEEL-8708703200-R1',
     '65000000-0000-4000-8000-000000000071'::uuid,
     'CLAUSE-MY-PDK2025-870870-ROUND1','CLAUSE-MY-CONTROL-8708703200-ROUND1',
     '8708703200','For vehicles of heading 87.03',0.30,'kg',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"pdk.national_subdivision_branch","operator":"EQ","value":"32"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-ROAD-WHEEL-8708709700-R1',
     '65000000-0000-4000-8000-000000000071'::uuid,
     'CLAUSE-MY-PDK2025-870870-ROUND1','CLAUSE-MY-CONTROL-8708709700-ROUND1',
     '8708709700','For vehicles of heading 87.03',0.30,'kg',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"pdk.national_subdivision_branch","operator":"EQ","value":"97"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),

    ('MAP-MY-MFN-CCU-FOUNDATION-BRAKE-8708302100-R1',
     '65000000-0000-4000-8000-000000000081'::uuid,
     'CLAUSE-MY-PDK2025-870830-ROUND1','CLAUSE-MY-CONTROL-8708302100-ROUND1',
     '8708302100','Brake drums, brake discs or brake pipes',0.30,'kg',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"part.component_type","operator":"IN","value":["BRAKE_DRUM","BRAKE_DISC","BRAKE_PIPE"]}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-FOUNDATION-BRAKE-8708302900-R1',
     '65000000-0000-4000-8000-000000000081'::uuid,
     'CLAUSE-MY-PDK2025-870830-ROUND1','CLAUSE-MY-CONTROL-8708302900-ROUND1',
     '8708302900','Other brakes, servo-brakes and parts thereof',0.30,'kg',
     'SCHEDULE_ROWS_DISPLAYED','REPLACEMENT_BRAKING_PART_SCOPE_CONFIRMATION_REQUIRED',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"part.component_type","operator":"NOT_IN","value":["BRAKE_DRUM","BRAKE_DISC","BRAKE_PIPE"]}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),

    ('MAP-MY-MFN-CCU-STEERING-GEAR-COLUMN-8708949500-R1',
     '65000000-0000-4000-8000-000000000091'::uuid,
     'CLAUSE-MY-PDK2025-870894-ROUND1','CLAUSE-MY-CONTROL-8708949500-ROUND1',
     '8708949500','Steering wheels, steering columns and steering boxes; parts thereof - for vehicles of heading 87.03',0.25,'kg',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"part.component_type","operator":"IN","value":["STEERING_GEAR","STEERING_RACK","STEERING_COLUMN"]},{"field":"classification.separate_motor_or_ecu_reviewed","operator":"EQ","value":true}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),

    ('MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708801600-R1',
     '65000000-0000-4000-8000-000000000101'::uuid,
     'CLAUSE-MY-PDK2025-870880-ROUND1','CLAUSE-MY-CONTROL-8708801600-ROUND1',
     '8708801600','For vehicles of heading 87.03',0.30,'kg',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"pdk.national_subdivision_branch","operator":"EQ","value":"16"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status),
    ('MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708809200-R1',
     '65000000-0000-4000-8000-000000000101'::uuid,
     'CLAUSE-MY-PDK2025-870880-ROUND1','CLAUSE-MY-CONTROL-8708809200-ROUND1',
     '8708809200','For vehicles of heading 87.03',0.30,'kg',
     'NO_DATA','PORTAL_OBSERVATION_ONLY',
     '{"all":[{"field":"vehicle.intended_heading","operator":"EQ","value":"8703"},{"field":"pdk.national_subdivision_branch","operator":"EQ","value":"92"}]}'::jsonb,
     'CANDIDATE'::ref.verification_status)
),
prepared AS (
  SELECT
    r.*,
    tc.source_clause_id AS tariff_clause_id,
    cc.source_clause_id AS control_clause_id,
    cd.archived_object_key AS control_object_key
  FROM mapping_rows r
  JOIN evidence.source_clause tc ON tc.clause_code = r.tariff_clause_code
  JOIN evidence.source_clause cc ON cc.clause_code = r.control_clause_code
  JOIN evidence.source_document cd
    ON cd.source_document_id = cc.source_document_id
)
INSERT INTO customs.tariff_mapping (
  mapping_code, country_id, candidate_id, tariff_version,
  national_tariff_code, tariff_description, origin_regime,
  trade_agreement_id, duty_rate, rate_type, additional_measure,
  eligibility_condition, effective_from, effective_to, version,
  source_clause_id, record_status, verification_status
)
SELECT
  p.mapping_code,
  (SELECT country_id FROM ref.country WHERE iso2 = 'MY'),
  p.candidate_id, 'PDK 2025', p.national_tariff_code,
  p.tariff_description, 'MFN', NULL, p.duty_rate,
  CASE WHEN p.duty_rate = 0 THEN 'ZERO'::ref.rate_type
       ELSE 'AD_VALOREM'::ref.rate_type END,
  jsonb_build_object(
    'customs_unit', p.unit_code,
    'sst', jsonb_build_object(
      'displayed_rate', 0.10,
      'portal_display_verified', true,
      'calculation_rule_code', 'RULE-MY-SST-IMPORT-BASE-2018'
    ),
    'portal_import_control', jsonb_build_object(
      'result', p.portal_control_status,
      'scope_assessment', p.portal_control_scope,
      'observed_on', '2026-07-28',
      'source_clause_id', p.control_clause_id,
      'archived_object_key', p.control_object_key,
      'legal_conclusion', false
    ),
    'verification_scope',
    'PDK national line, MFN duty and displayed SST verified; final CCU classification is conditional on eligibility fields'
  ),
  p.eligibility_condition, DATE '2025-11-01', NULL, 1,
  p.tariff_clause_id, 'ACTIVE', p.verification_status
FROM prepared p
ON CONFLICT (mapping_code, version) DO UPDATE
SET country_id = EXCLUDED.country_id,
    candidate_id = EXCLUDED.candidate_id,
    tariff_version = EXCLUDED.tariff_version,
    national_tariff_code = EXCLUDED.national_tariff_code,
    tariff_description = EXCLUDED.tariff_description,
    origin_regime = EXCLUDED.origin_regime,
    trade_agreement_id = EXCLUDED.trade_agreement_id,
    duty_rate = EXCLUDED.duty_rate,
    rate_type = EXCLUDED.rate_type,
    additional_measure = EXCLUDED.additional_measure,
    eligibility_condition = EXCLUDED.eligibility_condition,
    effective_from = EXCLUDED.effective_from,
    effective_to = EXCLUDED.effective_to,
    source_clause_id = EXCLUDED.source_clause_id,
    record_status = EXCLUDED.record_status,
    verification_status = EXCLUDED.verification_status,
    updated_at = now();

-- ---------------------------------------------------------------------------
-- 5. Preserve unresolved enterprise and authority inputs
-- ---------------------------------------------------------------------------

WITH enterprise_rows (
  ccu_code, field_suffix, description, priority, next_action
) AS (
  VALUES
    ('CCU-TRACTION-MOTOR','motor_technology_and_rated_output',
     'Final motor line requires current type, continuous rated output in kW, integrated gearbox/inverter state and the applicable PDK national subdivision branch.',
     'P0'::ref.priority,
     'Enterprise to provide datasheet/nameplate and assembly drawing; classification owner to resolve the 850152 12/22/32 branch or retain 8501531000 when output exceeds 75 kW.'),
    ('CCU-TRACTION-INVERTER','primary_and_integrated_functions',
     'The verified conditional 8504404000 route requires inverter primary function and confirmation that integrated DC-DC/OBC functions do not change classification.',
     'P1'::ref.priority,
     'Enterprise to provide block diagram, electrical input/output and integrated-function list.'),
    ('CCU-ONBOARD-CHARGER','rating_and_conversion_function',
     'Selection among 8504402000, 8504403000 and 8504409000 requires kVA rating, AC/DC conversion description, bidirectional function and integrated DC-DC details.',
     'P0'::ref.priority,
     'Enterprise to provide charger rating plate, power-flow diagram and integrated-function specification.'),
    ('CCU-DC-DC-CONVERTER','integrated_charger_function',
     'The 8504409000 candidate requires confirmation that the unit is primarily a DC-DC converter and is not an integrated charger or inverter.',
     'P0'::ref.priority,
     'Enterprise to provide power-flow diagram, voltage levels, rating and integrated-function list.'),
    ('CCU-PASSENGER-BODY-SHELL','body_completeness_and_shipment_set',
     'The 8707109000 candidate and GRI 2(a) route depend on closures, glass, trim, shipment assembly state and the other vehicle components presented together.',
     'P0'::ref.priority,
     'Enterprise to provide body-shell BOM, photos/drawings, packing list and the complete CKD/SKD shipment set.'),
    ('CCU-ROAD-WHEEL','wheel_form_and_national_branch',
     'Four PDK passenger-vehicle branches remain because the portal omits their parent indentation labels; exact wheel form, material, tyre/hub presentation and branch basis are required.',
     'P0'::ref.priority,
     'Enterprise to provide wheel drawing, material, tyre/hub presentation and part description; classification owner to confirm the PDK parent branch.'),
    ('CCU-FOUNDATION-BRAKE','brake_component_and_intended_use',
     'Selection between 8708302100 and 8708302900 requires the exact included component and whether the goods are OEM KD components or replacement parts.',
     'P0'::ref.priority,
     'Enterprise to provide component-level BOM, brake type, included disc/drum/pipe/caliper/pads and intended-use declaration.'),
    ('CCU-STEERING-GEAR-COLUMN','steering_component_and_integrated_electrics',
     'The 8708949500 candidate requires exact component type and review of separately classifiable electric motor or ECU content.',
     'P1'::ref.priority,
     'Enterprise to provide assembly drawing, assist type and integrated motor/ECU details.'),
    ('CCU-SHOCK-ABSORBER-STRUT','damper_configuration_and_national_branch',
     'Selection between 8708801600 and 8708809200 requires the missing national parent branch plus confirmation whether the item is a shock absorber, strut or broader suspension assembly.',
     'P0'::ref.priority,
     'Enterprise to provide drawing, configuration, spring/knuckle content and electronic-control details; classification owner to confirm the PDK parent branch.')
)
INSERT INTO audit.missing_data (
  calculation_run_id, field_path, description, data_owner,
  data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
)
SELECT
  NULL,
  'enterprise.classification_input[' || e.ccu_code || '].' || e.field_suffix,
  e.description, 'ENTERPRISE_TECHNICAL_OWNER',
  'ENTERPRISE_INPUT', 'ENTERPRISE',
  'FINAL_NATIONAL_TARIFF_SELECTION_FOR_' || e.ccu_code,
  e.priority, e.next_action, NULL, 'WAITING_ENTERPRISE'
FROM enterprise_rows e
WHERE NOT EXISTS (
  SELECT 1 FROM audit.missing_data m
  WHERE m.field_path =
    'enterprise.classification_input[' || e.ccu_code || '].' || e.field_suffix
);

-- The public first-round tariff mapping is complete, but final line selection
-- remains waiting on the enterprise facts above. Do not mark it RESOLVED.
UPDATE audit.missing_data m
SET description =
      'First-round PDK 2025 candidate lines and displayed rates are recorded; final national tariff selection remains conditional on enterprise technical inputs and, where noted, the omitted national indentation.',
    data_owner = 'CUSTOMS_CLASSIFICATION_OWNER_AND_ENTERPRISE',
    data_kind = 'ENTERPRISE_INPUT',
    data_ownership = 'MIXED',
    priority = 'P0',
    next_action =
      'Supply the CCU-specific technical fields listed in audit.missing_data, then approve one candidate line or seek a customs ruling.',
    status = 'WAITING_ENTERPRISE',
    resolved_at = NULL
WHERE m.field_path LIKE 'customs.tariff_mapping[CCU-%].national_tariff_code'
  AND m.field_path NOT LIKE '%CCU-HV-BATTERY-PACK%';

WITH authority_rows (
  field_path, description, blocking_scope, priority, next_action
) AS (
  VALUES
    ('rules.import_control[8504409000].legal_scope_and_effective_date',
     'The portal displays Schedule 4 Part 2 controls for chargers/domestic apparatus and wireless WPT, but the legal effective date and applicability to an automotive OBC or integrated DC-DC unit have not been established.',
     'IMPORT_CONTROL_FOR_8504409000','P1'::ref.priority,
     'Archive the controlling prohibition order and obtain ST/SIRIM confirmation if the product may match the described charger or wireless/WPT scope.'),
    ('rules.import_control[8707109000].required_document_and_effective_date',
     'The portal displays Schedule 2 Part 2 and MITI for vehicle bodies, while OGA Code and Mandatory fields are blank and the exact permit/document is not stated.',
     'IMPORT_CLEARANCE_FOR_BODY_SHELL','P0'::ref.priority,
     'Review the controlling prohibition order and obtain MITI confirmation of AP/import-licence category and required documents for the project.'),
    ('rules.import_control[8708302900].oem_kd_vs_replacement_scope',
     'The portal control text is expressly for replacement braking-system parts; application to OEM parts imported under a KD programme remains unconfirmed.',
     'IMPORT_CLEARANCE_FOR_BRAKE_PARTS','P0'::ref.priority,
     'Confirm intended use with the enterprise and obtain JKDM/JPJ confirmation before applying or excluding the displayed certification requirements.')
)
INSERT INTO audit.missing_data (
  calculation_run_id, field_path, description, data_owner,
  data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
)
SELECT
  NULL, a.field_path, a.description, 'MALAYSIA_AUTHORITY_OWNER',
  'AUTHORITY_CONFIRMATION', 'PUBLIC', a.blocking_scope,
  a.priority, a.next_action, 'https://ezhs.customs.gov.my/',
  'WAITING_AUTHORITY'
FROM authority_rows a
WHERE NOT EXISTS (
  SELECT 1 FROM audit.missing_data m WHERE m.field_path = a.field_path
);

WITH research_rows (
  field_path, description, next_action
) AS (
  VALUES
    ('customs.pdk2025.omitted_parent_indentation[850152]',
     'The portal result lists three vehicle lines 8501521200/2200/3200 but does not expose the parent labels distinguishing those branches.',
     'Read the controlling PDK 2025 schedule page or request JKDM classification confirmation before choosing the 12/22/32 branch.'),
    ('customs.pdk2025.omitted_parent_indentation[870870]',
     'The portal result lists four heading-8703 branches but omits the parent labels distinguishing wheel/part groups.',
     'Read the controlling PDK 2025 schedule page or request JKDM classification confirmation before choosing 16/22/32/97.'),
    ('customs.pdk2025.omitted_parent_indentation[870880]',
     'The portal result lists 8708801600 and 8708809200 for heading 8703 but omits the parent labels distinguishing the two groups.',
     'Read the controlling PDK 2025 schedule page or request JKDM classification confirmation before choosing 16 or 92.'),
    ('customs.pdk2025.omitted_parent_indentation[870894]',
     'The portal result does not expose the parent label distinguishing the 11/19 group from the 94/95/99 group.',
     'Read the controlling PDK 2025 schedule page or request JKDM classification confirmation before final approval of 8708949500.')
)
INSERT INTO audit.missing_data (
  calculation_run_id, field_path, description, data_owner,
  data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
)
SELECT
  NULL, r.field_path, r.description, 'CUSTOMS_CLASSIFICATION_OWNER',
  'PUBLIC_RESEARCH', 'PUBLIC', 'FINAL_PDK_NATIONAL_BRANCH',
  'P1', r.next_action, 'https://ezhs.customs.gov.my/', 'IN_RESEARCH'
FROM research_rows r
WHERE NOT EXISTS (
  SELECT 1 FROM audit.missing_data m WHERE m.field_path = r.field_path
);

COMMIT;
