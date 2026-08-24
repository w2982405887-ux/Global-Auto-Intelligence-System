\pset null '[NULL]'
\x off

SELECT 'ref.country.country_name_cn' AS field_name,
       count(*) FILTER (WHERE country_name_cn LIKE '%?%') AS corrupted_rows
FROM ref.country
UNION ALL
SELECT 'evidence.source_clause.translated_text_cn',
       count(*) FILTER (WHERE translated_text_cn LIKE '%?%')
FROM evidence.source_clause
UNION ALL
SELECT 'rules.country_rule_card.rule_name_cn',
       count(*) FILTER (WHERE rule_name_cn LIKE '%?%')
FROM rules.country_rule_card
UNION ALL
SELECT 'rules.country_rule_card.rule_content',
       count(*) FILTER (WHERE rule_content LIKE '%?%')
FROM rules.country_rule_card
UNION ALL
SELECT 'customs.customs_classification_unit.ccu_name_cn',
       count(*) FILTER (WHERE ccu_name_cn LIKE '%?%')
FROM customs.customs_classification_unit
UNION ALL
SELECT 'rules.tax_scenario_model.scenario_name_cn',
       count(*) FILTER (WHERE scenario_name_cn LIKE '%?%')
FROM rules.tax_scenario_model;

SELECT rule_code, rule_name_cn,
       encode(convert_to(rule_name_cn, 'UTF8'), 'hex') AS utf8_hex
FROM rules.country_rule_card
ORDER BY rule_code;

SELECT ccu_code, ccu_name_cn
FROM customs.customs_classification_unit
ORDER BY ccu_code;
