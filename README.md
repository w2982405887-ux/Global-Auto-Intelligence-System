# Global Automotive KD Intelligence System

面向汽车企业海外市场、CBU/KD 路径、海关归类、税务与审批决策的可追溯规则系统。

## 项目交接入口

最新的架构、数据库导出、两国计算口径、BOM缺口和进度说明：

```text
docs/PROJECT_HANDOFF_2026-08-25.md
```

数据库结构快照与恢复说明：

```text
database/exports/README.md
```

## 当前阶段

Phase 4：马来西亚项目级BOM/CCU计算与审计留痕。当前仓库已经建立：

- 数据合同、数据库迁移和FastAPI后端；
- 马来西亚五路径决策模型；
- PDK 2025、ACFTA、RCEP整车税率数据；
- 60个CCU及现有零件税率映射；
- 企业参数收集、计算、审计和AI安全视图；
- CCU税率及利润比较的Preview/Run接口。
- AutoPolicy前端及FastAPI只读数据库接入；
- 国家概览、五路径、规则证据、整车税率和CCU目录API。

当前前端首页、马来西亚五路径面板和`/decision/new`决策向导已读取真实API。
第二阶段已接通项目创建、五路径判定、企业参数、审批状态和税号显式选择；
第三阶段已接通项目级Preview、正式Run、Calculation Line、Decision Trace、
Missing Data和LLM安全视图。CBU在税率与税基完整时可执行完整税链；CKD按
已知进口环节计算并显式标记本地成车税负缺口。第四阶段已接通项目BOM/CCU
价值分配、每行MFN/ACFTA/RCEP映射的显式选择、三制度横向比较，以及正式Run的
输入快照、Calculation Line、Decision Trace和Missing Data持久化。优惠资格未经
确认时自动回退MFN，不输出虚假的优惠税负。系统禁止LLM直接计算税额或决定最终归类。

当前主账号路径为个人邮箱/密码账号：每人一个账号，不要求企业组织；AI聊天记录按
`user_id` 隔离。企业 OIDC、组织和RBAC结构仍保留作为兼容能力。浏览器只保存
`HttpOnly` 会话 Cookie，并通过双提交 CSRF 保护状态变更。

## 核心数据链

```text
企业料号 → 海关归类单元（CCU）→ HS6 候选 → 国家完整税号映射
       → 适用规则/审批 → 确定性计算 → 可审计输出
```

研究粒度是 CCU，不是企业的每个物理料号。企业料号通过带有效期和审核状态的映射挂接 CCU。

## 目录

```text
docs/                         架构、范围和 Excel 复用说明
spec/
  database_schema.yaml        逻辑数据合同
  enums.yaml                  跨层稳定枚举
  calculation_dsl.schema.json 安全、可校验的计算 DSL
backend/                      FastAPI/SQLAlchemy业务接口
frontend/                     AutoPolicy React/Vinext前端
database/migrations/          PostgreSQL 迁移
storage/                      证据文件对象存储占位
tests/                        规范和骨架测试
```

前端接入与五路径接口规划：

```text
docs/frontend_database_integration_guide.md
```

马来西亚五路径规则、企业必填字段及官方来源：

```text
docs/malaysia_five_route_tax_model.md
```

## 设计优先级

1. 原子记录：一行只表达一条独立规则或事实。
2. 时间版本：使用 `[effective_from, effective_to)`，结束日期为空表示持续有效。
3. 来源追溯：规则、税号映射和审批要求必须指向证据条款。
4. 条件可执行：条件与公式使用结构化 JSON，不执行任意字符串表达式。
5. 确定性计算：Python 引擎计算，LLM 只做提取、解释和报告。
6. 审核优先：候选归类、优惠资格和审批状态均保留人工审核入口。

## 本地启动（依赖安装后）

```powershell
docker compose up -d postgres

cd backend
$env:GAIS_DATABASE_URL="postgresql+psycopg://gais:<password>@127.0.0.1:5432/global_auto"
uvicorn app.main:app --reload

cd ..\frontend
Copy-Item .env.example .env.local
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

本地入口：

- 前端：`http://127.0.0.1:3000/`
- API文档：`http://127.0.0.1:8000/docs`
- 健康检查：`GET /health`
- 阶段元数据：`GET /meta/phase`

### 账号与权限

先执行并验证 IAM、对话历史和个人账号迁移：

```powershell
.\scripts\db-migrate-0011-iam-core.ps1
.\scripts\db-verify-0011-iam-core.ps1
.\scripts\db-migrate-0012-assistant-history.ps1
.\scripts\db-migrate-0013-personal-accounts.ps1
```

个人账号注册/登录是当前默认入口，不要求组织。`GAIS_AUTH_LOCAL_DEV_ENABLED` 仅用于
旧的开发登录，不应在生产环境开启。服务器必须使用随机 `GAIS_AUTH_SECRET_KEY`，
并通过 Secret Manager 注入；OIDC为可选兼容模式。

主要接口：

```text
GET  /api/v1/auth/config
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/oidc/start
GET  /api/v1/auth/oidc/callback
POST /api/v1/auth/dev/login        # 仅 local/dev/test 且显式开启
GET  /api/v1/auth/me
POST /api/v1/auth/logout
POST /api/v1/auth/revoke-all
GET  /api/v1/organizations
POST /api/v1/organizations/{id}/switch
GET  /api/v1/organizations/{id}/members
POST /api/v1/organizations/{id}/members/invitations
PATCH /api/v1/organizations/{id}/members/{membership_id}
```

已接通的查询API：

```text
GET /api/v1/dashboard/overview
GET /api/v1/countries/MY/overview
GET /api/v1/countries/MY/tax-routes
GET /api/v1/countries/MY/rules
GET /api/v1/countries/MY/vehicle-tariffs
GET /api/v1/ccus
GET /api/v1/ccus/{ccu_code}
GET /api/v1/ccus/{ccu_code}/tariff-options
```

已接通的决策写入API：

```text
POST /api/v1/countries/{iso2}/tax-routes/resolve
POST /api/v1/projects
GET  /api/v1/projects/{project_id}
PUT  /api/v1/projects/{project_id}/route-facts
GET  /api/v1/projects/{project_id}/inputs
PUT  /api/v1/projects/{project_id}/inputs/{field_path}
GET  /api/v1/projects/{project_id}/completion
GET  /api/v1/projects/{project_id}/approval-readiness
PUT  /api/v1/projects/{project_id}/approvals/{requirement_code}
PUT  /api/v1/projects/{project_id}/tariff-selections/{scope}
GET  /api/v1/projects/{project_id}/bom-lines
PUT  /api/v1/projects/{project_id}/bom-lines/{line_no}
DELETE /api/v1/projects/{project_id}/bom-lines/{line_no}
PUT  /api/v1/projects/{project_id}/bom-lines/{line_no}/tariff-selections/{regime}
POST /api/v1/projects/{project_id}/bom-comparison/preview
POST /api/v1/projects/{project_id}/bom-comparison/run
POST /api/v1/projects/{project_id}/calculations/preview
POST /api/v1/projects/{project_id}/calculations/run
GET  /api/v1/calculations/{run_id}
GET  /api/v1/calculations/{run_id}/trace
GET  /api/v1/calculations/{run_id}/missing-data
```

## 下一阶段入口

1. 增加BOM批量导入、编辑、删除及同一CCU多料号聚合；
2. 增加FTA资格确认控件与原产地证据挂接，区分法定结果和模拟结果；
3. 增加本地成车法定消费税率、销售税率及项目优惠批准的结构化选择；
4. 实现CBU、整套CKD、零件级与混合KD的跨路径税负和利润统一排名；
5. AI仅解释已保存的确定性结果、缺失项、来源与计算过程。
