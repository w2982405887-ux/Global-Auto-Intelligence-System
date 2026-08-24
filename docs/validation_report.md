# Phase 1 骨架验证报告

验证日期：2026-07-27

## 已通过

- `calculation_dsl.schema.json` 可被标准 JSON 解析；
- DSL 中 14 个本地 `$defs` 均存在，35 次本地引用无悬空引用；
- 两份 YAML 不含 Tab，顶层版本、schema、枚举和跨表不变量区块存在；
- PostgreSQL 迁移包含事务边界，括号平衡；
- 首批核心表、CCU 候选、三类风险标签、计算和审计表均存在；
- Python 应用和测试文件通过 `compileall`；
- `pyproject.toml` 可由 Python 标准库解析；
- SQL 迁移不包含 `INSERT`，因此没有填充真实政策或税率数据。

## 环境限制

当前捆绑 Python 环境没有预装 `pytest`、`PyYAML` 和 `jsonschema`，因此没有在本次会话中执行
完整测试套件或 PostgreSQL 实例迁移。安装 `backend/pyproject.toml` 的开发依赖后，
`tests/test_contracts.py` 会完成 YAML 解析和 JSON Schema 元规范校验。

## 上库前必须补做

1. 在临时 PostgreSQL 15+ 数据库执行 `0001_phase1_core.sql`；
2. 运行 `pytest -q`；
3. 用一份不含真实税率的合成场景验证 DSL；
4. 对有效期重叠、版本关闭和审核状态增加数据库集成测试；
5. 经业务、海关和税务负责人共同冻结 v0.1 数据合同。
