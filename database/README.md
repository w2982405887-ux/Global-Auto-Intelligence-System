# Database

数据库以 PostgreSQL 15+ 为目标，Supabase PostgreSQL 可直接采用。

## 迁移

`migrations/0001_phase1_core.sql` 建立 Phase 1 所需的八个 schema、核心表、关联表、
必要索引和约束。迁移不包含任何真实政策、税率、税号或企业数据。

执行前应：

1. 创建独立的空数据库或 Supabase 开发项目；
2. 使用迁移专用角色；
3. 对照 `spec/database_schema.yaml` 审核；
4. 在事务中执行；
5. 保存迁移日志和数据库结构快照。

## 约束策略

- 业务表使用 UUID 内部主键与可读业务代码；
- 百分率以小数存储，例如 `0.10` 表示 10%；
- `effective_to` 为空表示开放区间，否则必须大于 `effective_from`；
- 未知税率使用 `NULL + UNKNOWN`，禁止写成 0；
- 核心规则、映射和审批记录必须挂接 `source_clause_id`；
- 企业料号不含最终 HS 字段；
- 场景与规则、审批通过关联表连接，不在 JSON 数组中存外键。
