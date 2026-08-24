# Backend skeleton

当前后端只提供：

- FastAPI 应用入口；
- Pydantic 配置；
- SQLAlchemy 连接与基类；
- 规范加载和 DSL 校验入口；
- 明确拒绝未实现计算的占位服务。

它不包含真实税率、最终税号判断、政策爬取、LLM 推理或 UI。

## 启动

复制 `.env.example` 为本地环境变量配置并安装依赖后：

```powershell
uvicorn app.main:app --reload
```

## 迁移

Phase 1 的权威迁移位于 `../database/migrations/0001_phase1_core.sql`。
Alembic 在下一阶段根据已冻结的数据合同建立基线，避免 Phase 1 同时维护两份不同的 DDL。
