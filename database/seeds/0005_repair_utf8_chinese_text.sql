BEGIN;

UPDATE ref.country
SET country_name_cn = CASE iso2
  WHEN 'MY' THEN '马来西亚'
  WHEN 'CN' THEN '中国'
END
WHERE iso2 IN ('MY', 'CN');

UPDATE evidence.source_clause
SET translated_text_cn = CASE clause_code
  WHEN 'CLAUSE-MY-PDK2025-P4'
    THEN '第一附表货物的归类受协调制度归类总规则约束。'
  WHEN 'CLAUSE-MY-MITI-AP-CKD'
    THEN '以CBU或CKD方式进口的各类机动车和摩托车（包括商用车）属于AP监管对象。'
  WHEN 'CLAUSE-MY-PDK2025-8507603300-RATE'
    THEN '用于第87章车辆的锂离子蓄电池。'
  WHEN 'CLAUSE-MY-IMPORT-PROHIBITION-8507603300'
    THEN '用于所列第87章机动车辆的各种新可充电蓄电池。'
  WHEN 'CLAUSE-MY-MITI-BATTERY-AP-2026'
    THEN '自2026年1月1日起，所列机动车辆用各种新可充电蓄电池进口必须通过ePermit系统取得MITI签发的Approved Permit。'
  WHEN 'CLAUSE-MY-SALES-TAX-ACT-S9-IMPORT-VALUE'
    THEN '进口应税货物的销售税计税价值为海关完税价格、应付进口关税及应付消费税之和。'
  WHEN 'CLAUSE-MY-SALES-TAX-RATE-2025-P2'
    THEN '除适用税率令另有规定或属于免税货物外，应税货物销售税税率为10%。'
  WHEN 'CLAUSE-MY-ACFTA-8507603300-RATE-2026'
    THEN 'ACFTA税表中，车辆用锂离子蓄电池完整税号8507603300的2026当前税率为0。'
  WHEN 'CLAUSE-MY-RCEP-8507609000-RATE-2026'
    THEN 'RCEP税表未显示8507603300；HS6 850760下的其他锂离子蓄电池税号8507609000的2026当前税率为20%。'
  WHEN 'CLAUSE-MY-FTA-PROOF-OF-ORIGIN'
    THEN 'ACFTA使用Form E；RCEP使用Form RCEP或经核准出口商的原产地声明。申报时还应提交进口申报及支持文件；不同协定税号版本之间需要进行关联。'
  ELSE translated_text_cn
END
WHERE clause_code IN (
  'CLAUSE-MY-PDK2025-P4',
  'CLAUSE-MY-MITI-AP-CKD',
  'CLAUSE-MY-PDK2025-8507603300-RATE',
  'CLAUSE-MY-IMPORT-PROHIBITION-8507603300',
  'CLAUSE-MY-MITI-BATTERY-AP-2026',
  'CLAUSE-MY-SALES-TAX-ACT-S9-IMPORT-VALUE',
  'CLAUSE-MY-SALES-TAX-RATE-2025-P2',
  'CLAUSE-MY-ACFTA-8507603300-RATE-2026',
  'CLAUSE-MY-RCEP-8507609000-RATE-2026',
  'CLAUSE-MY-FTA-PROOF-OF-ORIGIN'
);

UPDATE rules.country_rule_card
SET
  rule_name_cn = CASE rule_code
    WHEN 'RULE-MY-GRI-2A-2025'
      THEN '不完整、未制成、未组装或拆散货物的GRI 2(a)风险'
    WHEN 'RULE-MY-SST-IMPORT-BASE-2018'
      THEN '进口货物销售税计税基础'
    WHEN 'RULE-MY-SST-RATE-8507603300-2025'
      THEN '8507603300进口销售税税率'
    WHEN 'RULE-MY-ACFTA-ORIGIN-DOCUMENT'
      THEN 'ACFTA优惠申报文件'
    WHEN 'RULE-MY-RCEP-ORIGIN-DOCUMENT'
      THEN 'RCEP优惠申报文件'
    ELSE rule_name_cn
  END,
  rule_content = CASE rule_code
    WHEN 'RULE-MY-GRI-2A-2025'
      THEN '当同一票或相关货物集合可能具备完整品的基本特征时，必须评估是否按完整品归类；本记录不自动得出整车结论。'
    WHEN 'RULE-MY-SST-IMPORT-BASE-2018'
      THEN '进口应税货物的销售税计税基础为海关完税价格、进口关税和消费税之和。'
    WHEN 'RULE-MY-SST-RATE-8507603300-2025'
      THEN 'PDK 2025 HS Explorer对8507603300显示SST 10%；适用时仍须检查特定免税资格。'
    WHEN 'RULE-MY-ACFTA-ORIGIN-DOCUMENT'
      THEN '中国原产货物主张ACFTA优惠时，应提交Form E、进口申报及海关要求的支持文件，并满足适用原产地规则。'
    WHEN 'RULE-MY-RCEP-ORIGIN-DOCUMENT'
      THEN '中国原产货物主张RCEP优惠时，应提交Form RCEP或经核准出口商的原产地声明、进口申报及支持文件，并满足适用原产地规则。'
    ELSE rule_content
  END,
  updated_at = now()
WHERE rule_code IN (
  'RULE-MY-GRI-2A-2025',
  'RULE-MY-SST-IMPORT-BASE-2018',
  'RULE-MY-SST-RATE-8507603300-2025',
  'RULE-MY-ACFTA-ORIGIN-DOCUMENT',
  'RULE-MY-RCEP-ORIGIN-DOCUMENT'
);

UPDATE customs.customs_classification_unit
SET ccu_name_cn = '锂离子动力电池包', updated_at = now()
WHERE ccu_code = 'CCU-HV-BATTERY-PACK';

UPDATE rules.tax_scenario_model
SET scenario_name_cn = '马来西亚BEV动力电池包普通进口MFN场景',
    updated_at = now()
WHERE scenario_code = 'SCN-MY-PARTS-BEV-BATTERY-MFN';

COMMIT;
