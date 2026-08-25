# AI Harness、OpenClaw 与完全内网化架构

基线：2026-08-25

本文是 AI 助手的架构审计和迁移说明，重点回答三件事：

1. 当前项目实际运行的 Harness、OpenClaw、模型、附件、搜索和政策同步链路是什么；
2. 哪些能力已经可用，哪些仍依赖外部网络或人工操作；
3. 如何把 AI 助手迁移为服务器内运行、默认不出网、可审计且可长期运行的内部助手。

本文只描述架构和部署边界，不把“计划中的完全内网能力”表述成已经完成的功能。

## 1. 可迁移的项目根目录约定

项目不应依赖某台电脑的绝对路径。所有脚本和文档均应把仓库根目录称为：

`<PROJECT_ROOT>`

约定如下：

- 代码、迁移、seed、规范和文档使用仓库内相对路径；
- 后端默认通过自身文件位置解析项目根目录，启动目录不应影响规则文件和上传目录；
- 数据库连接串、模型密钥、Gateway token、搜索密钥和生产路径通过服务器环境变量或 Secret Manager 注入；
- OpenClaw state、workspace、证据文件、附件和数据库备份属于部署数据，不随代码仓库复制；
- 交接时记录目标服务器上的实际 checkout 路径，但不把它写成系统固定路径。

示例（Windows）：

~~~text
git clone <private-repository-url>
Set-Location .\Global-Auto-Intelligence-System
# 以当前 checkout 为项目根目录；部署密钥通过 Secret Manager 注入
~~~

示例（Linux）：

~~~text
git clone <private-repository-url>
cd Global-Auto-Intelligence-System
# 以当前 checkout 为项目根目录；部署密钥通过 Secret Manager 注入
~~~

当前本机目录只是一个 checkout 实例，不是部署契约。迁移验收应以健康检查、数据库迁移、文件权限和服务间连通性为准。

| 数据 | 推荐位置 | 是否进 Git |
|---|---|---:|
| 代码、迁移、seed、规范、文档 | `<PROJECT_ROOT>` | 是 |
| PostgreSQL 连接串和认证密钥 | Secret Manager / 服务环境 | 否 |
| OpenClaw state/workspace | 服务器持久卷 | 否 |
| 证据原文件和附件 | 加密对象存储或受限持久卷 | 否 |
| 数据库结构快照 | database/exports/schema | 可提交纯结构快照 |
| 完整 dump、账号、聊天、企业 BOM | 加密备份介质 | 否 |

## 2. Harness 的定义与当前请求链路

本项目的 Harness 应理解为“AI 助手的控制平面”，不是某一个模型，也不是 OpenClaw 的网页界面。它负责：

- 识别请求和当前国家、日期、路径、动力类型等业务上下文；
- 管理附件、会话、账号隔离和历史消息；
- 将模型可调用能力限制在受控工具注册表；
- 执行确定性 CBU/CKD 计算、政策/证据查询和数据覆盖检查；
- 将工具结果包在来源、状态、完整度和限制条件中；
- 阻止模型把候选税号、搜索摘要或零税行写成确定结论；
- 输出 SSE、审计摘要和可追溯的计算/证据引用。

当前主要链路是：

~~~text
浏览器 :3000
    ↓ 仅访问 /api/v1/assistant/*
FastAPI :8000（Harness / 代理与安全边界）
    ├─ 会话、账号、附件和输入校验
    ├─ OpenClaw Gateway :18789（可选，loopback/private）
    ├─ Legacy LangGraph（OpenClaw 不可用时的回退）
    ├─ 确定性业务工具
    ├─ 内部 PostgreSQL / evidence / audit
    └─ 受控的外部搜索桥接（可选）
    ↓
模型或 OpenClaw 配置的上游提供商
~~~

当前是“FastAPI 代理 + 可选 OpenClaw + Legacy LangGraph + 可选外部模型/搜索”的混合架构，不是完全内网架构。

## 3. 当前实现事实

| 能力 | 当前实现 | 当前边界 |
|---|---|---|
| Harness 入口 | FastAPI assistant router | 浏览器不应直接访问模型或 Gateway |
| OpenClaw | services/openclaw_client.py，Gateway 默认 127.0.0.1:18789 | 可关闭；默认配置中 openclaw_enabled 为 false |
| 旧代理 | backend/app/agent/graph.py | 仍可作为回退；使用 OpenAI-compatible LLM 配置 |
| 确定性计算 | CBU/CKD Python tools 与数据库 | 计算结果优先于模型生成；缺失时必须显示 PARTIAL |
| 规则/证据 | policy、evidence、coverage 工具和 PostgreSQL | 证据状态与税率完整度必须分开 |
| 附件 | router 本地保存；pypdf 抽取 PDF；DOCX/XML 文本抽取；文本/JSON/CSV | 扫描 PDF 没有已验证的本地 OCR 管道 |
| 图片 | 以 data URL 传给 OpenClaw | 依赖上游模型支持视觉；当前未形成独立本地视觉/OCR服务 |
| 搜索 | Brave、Tavily、可配置 SearXNG 桥接；OpenClaw 也可有原生搜索 | 公共搜索结果仅作发现/佐证，不能覆盖内部确定性数据 |
| 数据库存储 | PostgreSQL；聊天按 user_id 隔离 | 生产凭证不得给模型或 OpenClaw |
| 调度 | 政策同步已有接口约定和调度选项 | 尚未验收一个独立、可恢复、可观测的生产 scheduler worker |
| 模型 | provider.py 默认 OpenAI-compatible；可配 OpenAI/DeepSeek/其他兼容端点 | 当前没有已验收的本地推理模型服务 |
| 容器隔离 | OpenClaw 本地测试 compose 已启用只读、无新权限、丢弃 capabilities、命令拒绝 | 这是降低风险的配置，不是“万无一失”证明 |

### 3.1 已实现的控制点

- 浏览器不会获得 OpenClaw Gateway token；
- OpenClaw Gateway 默认只绑定本机/private ingress；
- 工具调用使用 allowlist，禁止模型任意 SQL、shell、文件删除或补丁操作；
- 工具结果带 evidence gate，区分 VERIFIED、候选、未入库、搜索线索和不适用；
- 搜索结果不能自动把数据库缺口补成确定税率；
- 账号聊天记录绑定 user_id；
- 附件大小、类型和文本长度有后端限制；
- 上传目录和 OpenClaw state 应与代码、数据库备份分开管理。

### 3.2 当前不能宣称的能力

以下能力不能在当前状态下宣称已经完成：

- 完全不依赖外部网络的模型回答；
- 扫描 PDF 的稳定 OCR、版面还原和页码级引用；
- 本地视觉模型对图片的可重复识别；
- 本地向量检索和完整的文档知识库；
- 独立 scheduler 在服务器重启、失败、重复任务后的生产验收；
- 只允许官方域名出网的可验证隔离；
- 零风险的 OpenClaw 权限配置。

## 4. 目标：完全内网的内部助手

目标生产链路：

~~~text
账号/浏览器
    ↓
FastAPI Harness（唯一业务入口）
    ├─ Model Router（本地模型服务）
    ├─ Tool Registry（业务白名单）
    ├─ Attachment Pipeline（本地解析/OCR/索引）
    ├─ Retrieval（PostgreSQL + 本地全文/向量索引）
    ├─ Evidence Gate + Audit
    └─ Internal Scheduler
         ↓
内部 PostgreSQL / 证据库 / 加密对象存储 / 本地模型
~~~

完全内网模式的硬边界：

1. FastAPI、模型服务、OCR、检索、PostgreSQL、对象存储和 scheduler 使用服务器内网或同机网络；
2. 生产环境默认禁用公共搜索、OpenClaw 原生浏览器工具和任意外部 URL；
3. 模型只能调用注册的业务工具，不能得到数据库凭证、shell、文件系统写权限或容器管理权限；
4. 规则计算由 Python 确定性引擎执行，模型只负责意图解析、字段抽取、解释、摘要和报告；
5. 任何政策/税率改变必须经过 evidence、版本、生效日期和人工/规则核验；
6. 所有回答引用内部证据、计算行、规则版本和缺失数据；不能只显示模型文本；
7. 账号、聊天、附件和企业 BOM 按 user_id/授权边界隔离，日志默认脱敏；
8. 出网必须是显式的受控例外，并由网络层、服务配置和审计日志同时控制。

“完全内网”不等于把所有组件放在同一台机器。只要服务之间不需要公共互联网，且出网能力默认关闭、例外可审计，即可部署在企业私网或隔离区。

## 5. Harness 分层设计

| 层 | 责任 | 不能做什么 |
|---|---|---|
| Request boundary | 鉴权、CSRF、限流、上传校验、国家上下文 | 不把 token 交给浏览器 |
| Context builder | 会话、问题、附件摘要、当前业务参数 | 不凭模型猜国家/日期 |
| Intent/slot layer | 识别 CBU/CKD、车型、动力、排量、原产国等 | 不直接决定最终税号 |
| Tool registry | 注册计算、政策、证据、覆盖检查工具 | 不暴露任意 Python/SQL/shell |
| Tool executor | 参数校验、超时、去重、重试、结果封装 | 不把失败当 0% |
| Evidence gate | 完整度、来源层级、候选/确定状态 | 不让搜索覆盖已核验规则 |
| Model adapter | OpenClaw、云端 OpenAI-compatible 或本地模型统一接口 | 不把内部密钥放进消息 |
| Attachment pipeline | MIME/大小、解析、OCR、页码引用、索引 | 不把未扫描文件直接喂给生产模型 |
| Persistence | 对话、附件、工具摘要、审计、计算结果 | 不把敏感全文无期限写入日志 |
| Scheduler | 触发内部任务、重试、锁、告警 | 不直接给模型数据库管理员权限 |

建议在代码实现阶段将以上接口分别抽象为 ModelAdapter、ToolRegistry、EvidenceGate、AttachmentPipeline 和 SchedulerJob；OpenClaw 只是其中一种 ModelAdapter/执行后端。

## 6. 文档、PDF 和图片的内网处理

目标管道：

~~~text
上传
  ↓ MIME/大小/病毒/扩展名校验
加密对象存储（原件不可变）
  ↓
文本抽取 / OCR / 表格识别 / 页码定位
  ↓
Markdown + 结构化 JSON + page/block 引用
  ↓
人工抽样核验和 evidence.source_document/source_clause
  ↓
全文/向量索引
  ↓
按问题检索最小上下文
  ↓
模型解释 + 证据门禁
~~~

建议原则：

- 可抽取文本的 PDF/DOCX 先走本地解析，保留原文和页码；
- 扫描件使用服务器内 OCR，输出不确定字符和页码范围，不能静默覆盖原文；
- 表格税率同时保存原始单元格、标准化字段和解析置信度；
- 图片只作为证据候选，关键税号、日期、税率需人工确认；
- 模型上下文只读取当前问题所需片段，不把整个企业 BOM 或完整聊天记录发送给外部服务；
- 原件哈希、解析器版本、OCR 模型版本和人工复核状态必须可追溯；
- 外部识别服务只能作为隔离区的临时适配器，不能成为完全内网生产的必需依赖。

## 7. 全天候任务设计

### 7.1 纯内网生产模式（推荐默认）

可以每日运行的任务：

- 规则/税率有效期到期提醒；
- 数据库完整性、孤立映射、证据哈希和索引健康检查；
- 待人工核验政策队列整理；
- 已下载证据的本地重解析；
- 聊天/附件保留周期清理；
- 模型、OCR、检索服务健康检查；
- 本地政策包或人工导入文件的规范化入库。

这些任务不需要访问公共互联网。

### 7.2 受控采集区（可选）

如业务要求每日抓取最新政策，应把联网采集放在隔离的 collection worker 或专用网络区：

~~~text
允许访问的官方域名
    ↓ 只读下载、哈希、解析
候选 evidence package
    ↓ 单向/受保护导入
生产数据库 CANDIDATE
    ↓ 人工/规则审核
VERIFIED / RULING_CONFIRMED
~~~

采集区不持有生产数据库写凭证，不运行任意用户提示词，不执行 shell，不将网页内容直接当作政策。生产环境默认关闭公共搜索时，AI 仍可使用已审核的本地证据库回答。

OpenClaw Gateway 的 timer 可以作为触发器，但不应成为唯一的可靠调度器。推荐由 systemd timer、Kubernetes CronJob 或受控任务服务负责锁、重试、超时、失败告警和幂等。

## 8. 分阶段迁移方案

### 阶段 A：稳定当前混合架构

- 固定 FastAPI 为唯一 AI 入口；
- 将所有模型和搜索凭证移入 Secret Manager；
- 明确 OpenClaw 仅 private/loopback；
- 为每个工具补齐参数 schema、超时、重试、审计和错误状态；
- 附件保存、解析和聊天历史全部绑定账号；
- 以真实问题建立“工具调用成功、错误、重复、超时、空结果”的回归集；
- 交接文档和脚本统一使用 `<PROJECT_ROOT>`。

验收：重启后可恢复、无 token 泄露、工具不会越权、缺数据不生成确定税率。

### 阶段 B：形成稳定 Harness 接口

- 抽象 ModelAdapter，兼容 OpenClaw、云端 OpenAI-compatible 和本地模型；
- 统一 ToolResultEnvelope，携带 tool、输入摘要、结果、来源、状态、完整度和计算 ID；
- 将对话循环中的工具调用、最大轮数、去重、失效工具和重试集中管理；
- 增加结构化 AgentDecision/ASK_USER，而不是依赖自由文本正则；
- 将 comparison、CBU/CKD 结果比较放在确定性节点；
- SSE 事件统一为 request、status、tool_started、tool_completed、answer_delta、answer_completed、error 等可恢复事件。

验收：模型切换不改变业务计算；同一输入可重放；用户可看到来源和缺失项。

### 阶段 C：本地模型和默认断网

- 在服务器部署经过评测的本地推理服务；
- Model Router 默认只指向内网地址；
- 防火墙阻断模型服务和生产 Harness 的公网出口；
- 外部搜索、远程模型和 OpenClaw 原生 web 工具改为显式 break-glass；
- 对本地模型做中文、越南/马来西亚政策、表格、工具调用和拒答评测。

验收：断网条件下，基于已入库规则和上传文档的常用问题仍可回答；外部依赖缺失不会绕过证据门禁。

### 阶段 D：本地 OCR、检索和知识库

- 部署本地 PDF/DOCX 解析、OCR、表格识别；
- 建立原件、Markdown、结构化条款和页码引用的版本链；
- PostgreSQL 全文检索，必要时增加内网向量服务；
- 将政策证据、税率表、BOM和历史计算结果分层索引；
- 对解析错误、表格错位和扫描件进行抽样验收。

验收：上传官方 PDF/图片后可在内网完成解析、检索、引用和审计。

### 阶段 E：全天候内部助手

- 将内部健康检查、政策包导入、有效期提醒、索引、审计和备份做成独立 SchedulerJob；
- 每项任务有幂等键、锁、超时、重试、死信/人工队列和告警；
- 采集区与生产区采用单向候选证据导入；
- 为管理员提供任务状态、来源、差异和回滚记录；
- 定期执行灾备恢复和权限审计。

验收：服务器重启、网络短断、重复任务和半途失败都不会破坏已核验数据。

## 9. 服务器保密与权限验收清单

上线前必须逐项验证：

- [ ] 公网无法访问 FastAPI、PostgreSQL、OpenClaw、模型服务和对象存储管理端口；
- [ ] OpenClaw Gateway 只接受 FastAPI 的私网请求；
- [ ] OpenClaw 容器使用固定镜像摘要、非 root、只读根文件系统、无新增 capability；
- [ ] OpenClaw/模型账号没有数据库、shell、宿主机文件、Docker socket 或 Kubernetes 管理权限；
- [ ] 生产默认禁用 web search 和任意 URL；例外有审批、域名白名单和审计；
- [ ] Secret Manager 中的密钥不出现在前端、日志、错误页面、Prompt 或工具结果；
- [ ] 附件原件、OCR结果、聊天记录和企业 BOM 有独立访问控制和加密备份；
- [ ] 账号隔离、会话撤销、CSRF、限流和审计已回归；
- [ ] 规则、税率和政策变更必须经过 evidence 和审核状态；
- [ ] 断网演练、备份恢复、模型不可用回退和工具超时均有记录。

## 10. 结论

当前项目已经具备一个受控的 AI 助手原型：FastAPI 代理、账号隔离、附件入口、确定性业务工具、OpenClaw 适配器、来源门禁和可选搜索均已存在。但它仍是混合架构，不能宣称“完全内网”或“无需外部连接”。

最重要的工程方向不是把 OpenClaw 的权限全部打开，而是把 Harness 做成唯一控制平面：模型可替换、工具可白名单、数据可追溯、附件可本地处理、搜索可关闭、任务可重放。完成阶段 A-E 后，才能把它稳定地迁移到服务器，形成全天候、默认不出网、面向企业内部的保密助手。
