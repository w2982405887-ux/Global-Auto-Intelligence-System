# Spec contracts

三份文件共同构成 Phase 1 的权威数据合同：

- `enums.yaml`：跨数据库、后端和审计输出共享的稳定枚举；
- `database_schema.yaml`：逻辑实体、粒度、字段、外键和跨表不变量；
- `calculation_dsl.schema.json`：场景条件和计算公式的 JSON Schema。

修改顺序：

1. 先提交规范变更；
2. 审核兼容性和历史数据影响；
3. 再生成数据库迁移和后端模型；
4. 最后更新测试和示例。

任何真实政策装载都不得反向覆盖规范文件。
