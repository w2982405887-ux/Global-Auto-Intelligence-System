# Phase 1 范围与验收边界

## 本阶段交付

- 项目目录和模块边界；
- 数据库逻辑规范与稳定枚举；
- 可校验、不可任意执行的计算 DSL；
- PostgreSQL 首批表结构；
- FastAPI/SQLAlchemy/Pydantic 空框架；
- 两个既有 Excel 的结构复用说明。

## 明确不做

- 不录入或推断真实税率、HS 税号、FTA 优惠结论；
- 不判断马来西亚 GRI 2(a)、AP 或优惠是否最终适用；
- 不开发界面、爬虫或向量检索；
- 不把 Excel 示例值当作经官方核验的生产数据；
- 不把企业料号直接绑定为最终 HS 结论。

## Phase 1 数据验收

每个核心实体必须能够回答：

1. 这条记录是谁、何时创建和审核的？
2. 该记录在什么日期区间有效？
3. 依据哪个官方文件和具体条款？
4. 条件能否由程序读取并判断？
5. 发生冲突、缺失或不确定时是否阻断计算？
6. 新版本是否保留旧版本而非覆盖？

## 首批建表顺序

1. `evidence.source_document`
2. `evidence.source_clause`
3. `rules.country_rule_card`
4. `customs.customs_classification_unit`
5. `customs.tariff_mapping`
6. `rules.approval_matrix`
7. `rules.tax_scenario_model`

同一迁移中建立必要的引用表、关联表、计算审计表和企业输入表，使首批核心表不存在悬空外键。

## 马来西亚 Demo 后续装载范围

仅在结构冻结后录入：

- PDK 版本和适用期间；
- GRI 2(a) 风险规则；
- EV 政策；
- AP 要求；
- CBU/KD 税制；
- 10 个 CCU 及每个 1—3 个 HS6 候选。

所有 Demo 值默认 `DRAFT` 或 `UNVERIFIED`，直到来源条款和人工审核齐备。
