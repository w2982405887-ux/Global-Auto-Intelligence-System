# 既有 Excel 结构复用说明

本说明来自对两个源工作簿的只读结构盘点；没有修改源文件，也没有把其中示例值视为已核验政策。

## 全球规划工作簿

可复用的结构包括：

- `政策事件库`：事件编号、国家、节点类型、政策分类、适用对象、KD 模式、法律状态和多个关键日期；
- `国家政策摘要`：国家层级的规则覆盖与状态摘要；
- `综合税率可计算性`：区分“有税率信息”和“具备完整计算条件”；
- `未完整可计算清单`：缺失部分、数据归属、公开检索状态、下一步动作、官方入口和优先级；
- `来源索引`：来源登记与检索入口；
- 市场/项目主数据：地区、国家、合作方、车型、KD 模式、预测量和产能。

这些结构分别落入 `rules`、`audit.missing_data`、`evidence` 和 `enterprise`，不复制成一张宽表。

## 马来西亚 Demo 工作簿

其最有价值的复用内容是完整审计链：

```text
Scenario / Vehicle / BOM / Part
→ Classification
→ TaxRule / Eligibility / Source
→ CalcRun / CalcLine
→ DecisionTrace / MissingData / LLM View
```

主要字段已归一化到以下对象：

| Excel 结构 | Phase 1 归一化对象 |
|---|---|
| Country | `ref.country` |
| Scenario | `enterprise.scenario_input` |
| Vehicle | `enterprise.vehicle_model` |
| Part | `enterprise.enterprise_part` |
| BOM | `enterprise.bom_version`, `enterprise.bom_line` |
| Classify | `enterprise.enterprise_part_ccu_link`, `customs.ccu_candidate_hs` |
| TaxRule | `rules.country_rule_card`, `customs.tariff_mapping` |
| Eligibility | `rules.approval_matrix` 与运行时资格结果 |
| Source | `evidence.source_document`, `evidence.source_clause` |
| CalcRun / CalcLine | `calc.calculation_run`, `calc.calculation_line` |
| DecisionTrace | `audit.decision_trace` |
| MissingData | `audit.missing_data` |
| LLM View | `ai.llm_view_item` |

## 有意修正的 Excel 局限

- 将“来源文件”和“具体条款”拆表；
- 将企业 Part 与 CCU 拆开，避免企业料号成为归类主数据；
- 将 HS6 候选与国家完整税号映射拆开；
- 将场景引用规则和审批要求改为关联表，避免在数组字段中存外键；
- 将自由文本公式替换为白名单 AST；
- 将来源、审核、有效期、版本号和状态设为核心字段而非备注字段。
