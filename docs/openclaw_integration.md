# AutoPolicy AI 助手：OpenClaw 接入说明

> 本文描述当前的受控混合运行方式，不等于“完全内网”方案。FastAPI 是 Harness
> 控制平面和唯一业务入口；OpenClaw 是可选的模型/执行适配器。完全内网目标、
> 本地模型/OCR/检索和全天候任务迁移见
> `docs/AI_HARNESS_OFFLINE_ARCHITECTURE.md`。

## 请求链路

```text
浏览器 :3000
  │ 仅调用 /api/v1/assistant/*
  ▼
FastAPI :8000（本项目代理）
  ├─ 校验会话、文件类型、大小和附件 ID
  ├─ 调用 OpenClaw :18789（仅本机/private network）
  ├─ 执行五类 AutoPolicy 业务工具 + 受控网络搜索
  └─ 记录会话、工具摘要和结果
  ▼
OpenClaw Gateway → 已配置的模型/搜索提供商
```

浏览器不会拿到 `OPENCLAW_GATEWAY_TOKEN`。OpenClaw 的 OpenAI-compatible HTTP
端点具有完整 operator 权限，必须继续保持 loopback/private ingress，不能直接暴露
到公网。

## 已实现接口

- `POST /api/v1/assistant/files`：上传 PDF、DOCX、文本、JSON/CSV 和常见图片；默认单文件 20 MB。
- `POST /api/v1/assistant/chat`：`attachment_ids` 引用已上传文件；后端把文档抽取文本、图片 data URL 和用户问题组成 OpenClaw 消息。
- `GET /api/v1/assistant/openclaw/health`：只返回 Gateway 状态，不返回 token。
- OpenClaw 多轮工具循环：`calculate_cbu_tax`、`calculate_ckd_tax`、`search_policy_rules`、`get_policy_evidence`、`inspect_data_coverage` 和 `gais_web_search`。

如果 OpenClaw 没有启用，且没有附件，聊天会回退到原 LangGraph；带附件的请求不会降级到无法读取附件的旧链路。

## 后端 `.env` 配置

```dotenv
GAIS_OPENCLAW_ENABLED=true
GAIS_OPENCLAW_BASE_URL=http://127.0.0.1:18789
GAIS_OPENCLAW_GATEWAY_TOKEN=<与 OpenClaw .env 相同的 token>
GAIS_OPENCLAW_MODEL=openclaw/default
GAIS_OPENCLAW_FALLBACK_TO_LEGACY=true

# 任选一个受控搜索方案；政策研究推荐 Tavily，普通广域检索可用 Brave
GAIS_WEB_SEARCH_PROVIDER=tavily
GAIS_TAVILY_API_KEY=<Tavily API key>
# 或：
GAIS_WEB_SEARCH_PROVIDER=brave
GAIS_BRAVE_API_KEY=<Brave Search API key>
# 或：GAIS_WEB_SEARCH_PROVIDER=searxng
# GAIS_SEARXNG_BASE_URL=http://your-private-searxng:8080
```

OpenClaw 容器的 `ops/openclaw-local-test/.env` 至少需要 Gateway token；模型凭证
（例如 `OPENAI_API_KEY`）和 Brave key 仍然留空，待管理员决定后再写入。当前本地
Compose 已提供两种受控模型入口：默认使用 OpenAI；若设置
`OPENCLAW_MODEL_PROVIDER=deepseek` 并提供 `DEEPSEEK_API_KEY`，启动脚本会选择官方
DeepSeek 模型路由，并把默认模型切换到
`deepseek/deepseek-v4-pro`（也可在 `.env` 中改为 `deepseek-v4-flash`）。
DeepSeek 文本模型不等同于视觉模型；如果要直接理解图片，应使用支持视觉输入的
模型或在代理层增加 OCR/视觉模型路由。不要把密钥写进前端或提交到仓库。

本地启动脚本会优先读取项目根目录 `.env`；如果根目录没有对应的 `GAIS_*` 配置，
开发环境才会回退读取 `ops/openclaw-local-test/.env`。服务器部署时应关闭这种便利
回退，改用独立的 secret manager 或服务环境变量注入。

## 迁移到服务器

复制 `ops/openclaw-local-test/`（包括 `state/` 和 `workspace/`），服务器使用新
Gateway token，固定镜像 digest，保持 18789 只对 FastAPI 可达。将附件目录迁移到
持久卷并按应用账号设置权限；不要使用 `docker compose down -v` 删除 state。

## 完全内网生产模式（目标，不是当前默认）

完全内网模式不应只是把 OpenClaw 的 Gateway 搬到服务器。需要同时满足：

1. Model Router 只指向服务器内网的本地推理服务；生产默认禁用 OpenAI/DeepSeek 等云端端点；
2. 生产防火墙阻断 FastAPI、模型服务、OpenClaw 和数据库的公网出口；如必须更新政策，使用独立隔离采集区，只导入候选 evidence package；
3. OpenClaw 只能调用业务工具白名单，不获得数据库凭证、任意 SQL、shell、Docker socket、宿主机文件写权限或容器编排权限；
4. PDF/DOCX 解析、扫描件 OCR、图片理解和检索均由内网服务完成，保留原件哈希、解析器/OCR版本、页码和人工复核状态；
5. Evidence gate 继续区分已核验规则、候选税号、搜索线索和不完整计算，搜索结果不能覆盖确定性计算；
6. scheduler、健康检查、失败重试和日志审计由独立受控任务服务完成，OpenClaw timer 只能作为可选触发器；
7. 上线前必须完成断网演练、权限扫描、备份恢复和模型不可用回退验收。

当前 `GAIS_OPENCLAW_ENABLED`、搜索 provider 和模型 API 配置仍允许外部依赖，因此在迁移完成前应在产品状态中明确显示“受控混合架构”，不可向用户承诺完全保密或完全不出网。
