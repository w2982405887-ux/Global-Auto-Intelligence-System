# Global Auto Intelligence System 项目交接

交接基线：2026-08-25

## 1. 接手者先看这里

项目目录：

```text
当前 Git checkout 的仓库根目录（不依赖固定用户目录）
```

AI Harness、OpenClaw、附件处理、完全内网目标和全天候任务见：

```text
docs/AI_HARNESS_OFFLINE_ARCHITECTURE.md
```

本系统用于汽车企业 CBU（整车进口）与 KD/CKD（散件进口、本地组装）的海关归类、税负计算、优惠匹配、方案比较和政策问答。核心原则是：

- 税号、税率、条件、生效日期和来源分层保存；
- Python 确定性引擎计算，LLM 不自行编造税率或直接决定最终归类；
- 缺少最终税号、税基或关键资格时输出 `PARTIAL`/缺失项，不把未知值当作 0；
- 每条政策、税率和计算结果均应能够追溯到来源及计算过程。

接手顺序：

1. 阅读本文件、根目录 `README.md`、`docs/architecture.md`；
2. 阅读 `database/migrations/0001` 至 `0013`，确认当前数据库版本；
3. 启动 PostgreSQL、后端和前端，访问健康检查与 API 文档；
4. 运行后端测试和前端构建；
5. 修改税务逻辑前，先确认目标国家、日期、进口路径、税号粒度、税基和来源；
6. 不得把 `.env`、API Key、完整数据库备份、账号数据、聊天记录或上传文件提交到 GitHub。

## 2. 技术架构与关键目录

| 层 | 技术/目录 | 责任 |
|---|---|---|
| 前端 | React 19、Vinext/Vite；`frontend/app` | 首页、CBU/CKD、方案对比、政策审核、AI助手、个人账号 |
| 后端 | FastAPI、SQLAlchemy、Pydantic；`backend/app` | API、确定性计算、规则/证据查询、鉴权、AI代理 |
| 数据库 | PostgreSQL 16；`database`、`compose.yaml` | 规则、税率、BOM、计算、审计、账号、聊天记录 |
| AI | `backend/app/agent`、`services/openclaw_client.py` | 工具调用、SSE、附件、联网检索、来源门禁 |
| 证据 | `storage/evidence` | 官方 PDF/HTML 等对象文件；不在 PostgreSQL dump 内 |
| 测试 | `tests`、`frontend/tests` | 计算、国家路由、账号、对话、OpenClaw、越南数据 |

重点实现文件：

- 马来西亚 CBU：`backend/app/services/cbu_calculator.py`
- 马来西亚 CKD：`backend/app/services/ckd_calculator.py`
- 归类解析：`backend/app/services/classification_resolver.py`
- 越南 CBU/CKD：`backend/app/services/vietnam_quick_estimate.py`
- 项目/BOM计算：`backend/app/services/project_bom.py`、`project_calculation.py`
- AI助手：`backend/app/agent/graph.py`、`agent/router.py`、`services/openclaw_client.py`
- 个人账号：`backend/app/auth`、`database/migrations/0013_personal_accounts.sql`
- 账号对话隔离：`backend/app/agent/history.py`、`database/migrations/0012_assistant_history.sql`

## 3. 本地启动与验收

前置：Python 3.12、Node.js 22.13+、Docker Desktop。

```powershell
$repo = (git rev-parse --show-toplevel)
Set-Location $repo
docker compose up -d postgres
.\scripts\backend-run.ps1
```

后端默认：`http://127.0.0.1:8000`；健康检查：`GET /health`；API文档：`/docs`。

另开终端：

```powershell
$repo = (git rev-parse --show-toplevel)
Set-Location (Join-Path $repo "frontend")
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

前端使用同源 `/api/v1`，开发代理默认转发到 `127.0.0.1:8000`，可通过
`VITE_DEV_API_PROXY_TARGET` 指向服务器或私网中的后端。不要在浏览器端硬编码后端绝对地址。

验证：

```powershell
cd backend
pytest -q

cd ..\frontend
npm run build
npm run lint
```

## 4. 数据库交接

### 4.1 当前结构

当前 PostgreSQL 数据库约 22 MB，包含 11 个业务 schema、55 张由结构快照直接创建的表、28 个 enum、13 个迁移和 27 个 seed。主要 schema：

| Schema | 内容 |
|---|---|
| `ref` | 国家、主管机关、贸易协定 |
| `evidence` | 来源文件、条款和定位信息 |
| `rules` | 国家规则卡、优惠、审批、税务场景、KD路径 |
| `customs` | CCU、HS候选、国家税号、MFN/FTA税率 |
| `enterprise` | 车型、零件、BOM、项目输入、税号选择 |
| `calc` | 计算运行和逐项税额 |
| `audit` | 决策轨迹、缺失信息、人工复核 |
| `iam`/`platform` | 账号、会话、兼容性组织模型、迁移记录 |
| `assistant` | 按账号归属的对话和消息 |
| `ai` | 提供给AI读取的安全视图 |

关键BOM链：

```text
enterprise_part
→ enterprise_part_ccu_link
→ customs_classification_unit
→ ccu_input_requirement / ccu_candidate_hs
→ tariff_mapping
→ bom_version / bom_line / project_bom_line
→ project_bom_tariff_selection
→ calc.calculation_run / calculation_line
→ audit.decision_trace / missing_data_item
```

注意：`platform.schema_migration` 不能单独代表全部脚本已执行；部分后续迁移曾由独立 PowerShell 脚本执行。迁移文件、seed、结构快照与实际备份必须一起交接。

### 4.2 已生成的导出物

- 可提交结构快照：`database/exports/schema/global_auto_schema_2026-08-25.sql`
- 本地完整备份：`database/exports/full/global_auto_full_2026-08-25.dump`
- 备份目录清单：`database/exports/full/global_auto_full_2026-08-25.list`
- 导出/恢复说明与SHA256：`database/exports/README.md`

完整 dump 已在独立临时数据库中成功恢复验证。完整 dump 含账号、聊天记录和业务数据，已被 `.gitignore` 排除，严禁上传 GitHub。`storage/evidence` 与 `storage/assistant_uploads` 不在 dump 中，需要另行加密归档。

## 5. 账号与AI助手现状

当前主路径是个人邮箱/密码账号：

- 每人一个账号，不要求企业组织；
- 密码使用 PBKDF2-SHA256 哈希，数据库不存明文；
- 会话使用后端 Cookie；
- `assistant.conversation.user_id` 绑定账号，不同账号聊天记录隔离；
- OIDC、组织和RBAC结构仍保留以兼容旧架构，但不是当前使用前提。

AI助手现有能力：SSE流式输出、PDF/DOCX/文本/JSON/CSV/图片上传、多轮工具调用、政策/证据查询、数据覆盖检查、CBU/CKD工具、Brave/Tavily/SearXNG接口。工具包括：

```text
calculate_cbu_tax
calculate_ckd_tax
search_policy_rules
get_policy_evidence
inspect_data_coverage
gais_web_search
```

OpenClaw由 FastAPI 代理，浏览器不能直接访问 Gateway token。OpenClaw默认可关闭并回退旧代理；部署时 `18789` 只能向 FastAPI 私网开放。模型、Gateway和搜索密钥只放 Secret Manager/服务器环境变量。

这里的 FastAPI 代理即当前 Harness 控制平面：负责请求上下文、工具白名单、确定性结果、证据门禁、附件和账号历史。OpenClaw 不是安全边界，也不是完全内网能力的证明。当前仍可配置云端 OpenAI-compatible/DeepSeek 模型和 Brave/Tavily/SearXNG，因此当前状态应标记为“受控混合架构”，不能标记为“完全内网”。扫描 PDF 的生产级 OCR、本地视觉模型、本地向量检索和可靠的独立 scheduler worker 尚未验收。

未来服务器部署应以 `docs/AI_HARNESS_OFFLINE_ARCHITECTURE.md` 的阶段 A-E 为准：先固定 Harness 为唯一入口，再替换为本地模型和本地 OCR/检索；生产默认断网，联网采集放入隔离采集区，只导入候选证据，不直接改写已核验规则。

已知风险：国家参数必须显式传递。马来西亚工具不能被用于回答越南税率；网络搜索只能补证据，不能覆盖确定性数据库结果。

## 6. 两个典型国家的计量方式

### 6.1 马来西亚

当前是成熟度最高的确定性模型，覆盖 CBU、整套CKD、N205、CCU零件级和混合KD五类路径。

CBU使用整车PDK 10位税号。以海关完税价格 `V`：

```text
进口关税 D = V × 关税率
消费税 E = (V + D) × 消费税率
销售税 S = (V + D + E) × 销售税率
边境综合税率 = (D + E + S) ÷ V
```

日期、原产国、MFN/ACFTA/RCEP资格、Form E/RCEP证明、动力类型、车身细分类别和排量共同决定税号/税率。FTA不满足时回退MFN；BEV、HEV、PHEV、EREV不能互相套用优惠。

整套CKD分两阶段：

```text
进口阶段：CKD海关价值 × 关税 + 条件性进口SST
本地阶段：消费税计税价值 × 消费税率 + 成车销售税计税价值 × 销售税率
```

本地阶段相对CKD进口价值使用 `excise_value_ratio` 和 `sales_value_ratio`。没有这两个估值系数或批准状态时，只能输出进口阶段/情景结果，不能称为完整综合税率。进口SST豁免和项目优惠必须显式确认，不能把“可能0%”写成自动0%。

零件级CKD使用：

```text
加权进口关税率 = Σ(零件海关价值 × 该零件适用税率) ÷ Σ零件海关价值
```

### 6.2 越南

业务范围限定为新车乘用车（轿车/SUV）。

CBU按国家整车税号执行完整进口税链：

```text
进口关税 D = V × 关税率
特别消费税 SCT = (V + D) × SCT税率
进口VAT = (V + D + SCT) × VAT税率
边境综合税率 = (D + SCT + VAT) ÷ V
```

输入至少包括日期、原产国/制度、FTA资格、动力类型、座位/车身类别、最终国家税号、海关价值；ICE/HEV/PHEV/EREV还需排量及混动优惠条件。缺一项关键税率即输出不完整，不以0代替。

当前越南CKD只完成“主要部件进口关税估算”：

```text
主要部件加权关税率 = Σ(部件价值占比 × 最终VN税号税率)
```

支持MFN、ACFTA、ATIGA、RCEP情景，但必须先确认每个部件最终国家税号和原产资格，禁止自动选最低税率。还需单独判断同批散件是否因具备整车基本特征而触发GRI 2(a)未组装整车归类。

越南CKD尚未完整数值化：进口VAT及抵扣、本地组装后SCT、本地VAT、终端销售税、98.49资格/退税时点和完整BOM。因此当前正确状态是 `PARTIAL_IMPORT_STAGE_ESTIMATED`，不能称为完整综合税率。

另有数据口径风险：`customs.vehicle_tariff_line`当前强制10位代码，而越南官方税则通常以8位为核心。部分导入数据使用扩展位。后续必须建立“官方8位税号 + 系统扩展/展示码”的明确映射，禁止只靠补零或截断。

## 7. 当前急需的BOM与项目数据

完整企业BOM优先字段：

| 优先级 | 字段 | 用途 |
|---|---|---|
| P0 | 企业零件号、名称、数量、单位 | 确定实际进口范围 |
| P0 | CCU/主要部件类别与技术事实 | 生成并筛选HS候选 |
| P0 | 最终国家税号及归类依据 | 锁定适用税率，不能只用HS6 |
| P0 | 单价、币种、CIF/海关价值、运保费分摊 | 计算逐件税额和加权税率 |
| P0 | 每行原产国、FTA资格、Form E/RCEP等证明 | 选择MFN/协定税率 |
| P0 | 进口日期、批次、同批装配关系 | 匹配版本并评估GRI 2(a) |
| P1 | 项目/制造/进口批准及优惠资格 | 判断MY AP/SST或VN 98.49能否落地 |
| P1 | 本地成车SCT/消费税和VAT/SST计税价值 | 完成CKD全周期税负 |
| P2 | 本地采购标记、本地化率、组装成本和销售价格 | 方案优化和利润比较 |

越南主要部件估算当前覆盖19类：动力电池、驱动电机、电控、汽油发动机、柴油发动机、变速箱/减速器、车身、底盘、悬架/车桥、转向、制动、轮胎/轮毂、热管理、线束、座椅、玻璃、车灯、仪表/显示屏、安全气囊/安全带。

没有企业BOM时可以使用标准化权重做方向性估算，但必须显示“行业/系统默认权重”，不能伪装成企业项目结果。最先向企业索取的五项是：**实际进口件、最终国家税号、海关价值、原产国、FTA证明状态**。

已知公开数据缺口：马来西亚 `CCU-CATALYTIC-CONVERTER` 缺RCEP，`CCU-ENGINE-BLOCK-OR-HEAD` 与 `CCU-ENGINE-FUEL-INJECTOR` 缺MFN/ACFTA/RCEP。越南应继续补齐主要部件最终8位口径、MFN/RCEP逐年税率和本地税链。

## 8. 安全、GitHub与迁移注意事项

- 根目录 `.env` 含本地数据库/认证密钥，已忽略；服务器部署前轮换所有本地密钥；
- `ops/openclaw-local-test/.env`、OpenClaw state/workspace、`storage`、完整dump、日志不得提交；
- GitHub只提交代码、迁移、seed、参考CSV、纯结构SQL和文档；建议使用私有仓库；
- 数据库恢复后必须在独立测试库执行迁移/校验，不覆盖生产库；
- PostgreSQL dump不包含证据/附件对象，必须单独加密备份并保持对象路径一致；
- 接手者提交前执行密钥扫描、后端测试、前端构建和恢复演练。

## 9. 目标与进度

| 目标 | 状态 | 下一步 |
|---|---|---|
| 个人账号/聊天隔离 | 完成 | 部署验收 |
| 马来西亚CBU | 较完整 | 真实车型回归 |
| 马来西亚CKD | 部分完成 | 企业BOM与本地税基 |
| 越南CBU | 部分完成 | 税号口径/年度税率复核 |
| 越南CKD进口估算 | 部分完成 | 真实BOM、HS、MFN/RCEP |
| 越南CKD完整税链 | 急需 | 进口VAT、本地SCT/VAT、98.49 |
| AI Harness/OpenClaw 混合链路 | 部分完成 | 工具、附件、回退、私网和稳定性验收 |
| 完全内网模型/OCR/检索 | 未开始 | 本地模型、OCR、全文/向量索引与断网验收 |
| 政策自动更新 | 规划中 | 隔离采集、候选证据、审核、幂等和告警 |
| 代码/数据库交接 | 本次完成 | 绑定远端并交付密钥外备份 |
