# AutoPolicy 前端接入马来西亚五路径数据库指南

版本：v0.1  
日期：2026-07-29  
适用对象：前端、后端、数据和AI集成同事

## 1. 结论

现有前端的视觉设计、首页布局和四个业务入口可以保留，不需要推倒重做。

需要重新设计的是：

1. 决策工具的业务流程；
2. 前端与后端的数据契约；
3. 企业必填数据的收集与阻断逻辑；
4. CBU、整套CKD、分总成、CCU和混合KD的计算入口；
5. 来源、规则版本、缺失数据和审批状态的展示；
6. AI只能解释数据库结果，不能自行选择税号或计算税率。

前端不得直接连接PostgreSQL。正确链路是：

```text
Browser / Web App
        ↓ HTTPS JSON
FastAPI业务接口
        ↓ SQLAlchemy / parameterized SQL
PostgreSQL
        ↓
结构化规则、税率、证据、企业输入、计算记录和审计轨迹
```

数据库账号、连接串和管理员权限不得进入浏览器环境变量、JavaScript包或前端日志。

## 2. 当前系统状态

### 2.1 已经存在

数据库已有：

- 五种马来西亚税务决策路径；
- 8个KD税务桶；
- 471条PDK 2025整车完整税号；
- 471条ACFTA当前整车税率记录；
- 647条RCEP当前整车税率记录；
- 60个CCU；
- 346条现有CCU税率映射；
- 国家规则、审批要求、来源文件和来源条款；
- 5个五路径计算场景；
- 企业CCU技术参数空位及完成度视图；
- Calculation Run、Calculation Line、Decision Trace、Missing Data和LLM View。

可直接供后端读取的主要视图：

```text
ai.v_malaysia_five_route_decision_current
ai.v_malaysia_five_route_readiness
ai.v_malaysia_vehicle_tariff_rates_current
enterprise.v_part_ccu_input_collection
enterprise.v_part_ccu_input_completion
```

### 2.2 当前FastAPI已经实现

```text
GET  /health
GET  /meta/phase
POST /calculations/malaysia/preview
POST /calculations/malaysia/run
```

当前计算接口只覆盖以CCU/BOM为核心的MFN、ACFTA、RCEP零件进口比较。

### 2.3 当前后端尚未支持

以下能力不能由现有接口直接完成：

- 五路径自动判定；
- CBU整车完整税号查询和计算；
- 整套CKD完整税号计算；
- 分总成税务桶计算；
- 混合KD价值分配；
- 本地组装成车消费税和销售税；
- CBU与CKD端到端利润比较；
- 按国家规则生成前端企业必填字段；
- 五路径计算记录的统一审计持久化。

尤其需要注意：

- 现有`ComparisonPersistence`把`import_mode`固定写为`CKD`；
- 现有持久化逻辑绑定三个旧的Golden场景；
- 现有`TariffRepository`读取的是`customs.tariff_mapping`，尚未读取
  `customs.vehicle_tariff_rate_line`；
- `/meta/phase`仍显示旧Phase 1说明。

在前端正式接入前，后端同事必须先完成本指南第7节接口。

## 3. 前端信息架构调整

### 3.1 首页“全球决策”

截图中的视觉与结构可以保留，但所有数字必须来自API。

建议卡片字段：

| 前端字段 | 后端来源 |
|---|---|
| 重点国家 | `ref.country`及国家就绪度服务 |
| 待生效节点 | 有未来`effective_from`的规则、税率和审批 |
| 关键数据缺口 | `audit.missing_data`开放记录 |
| 最新政策动态 | `evidence.source_document`＋受影响规则 |
| 数据完整度 | 国家就绪度API |

不要在前端写死“15、24、11”等数字。

### 3.2 “决策工具”

改成五步向导：

```text
项目与车型
  ↓
五路径判定
  ↓
企业参数和审批
  ↓
税制及FTA场景
  ↓
CBU/KD结果比较与审计
```

### 3.3 “政策与证据”

每个规则详情必须同时展示：

- `rule_code`；
- 中文名称和规则内容；
- 生效日期、失效日期、版本；
- 状态和验证状态；
- 条件表达式；
- 来源机关；
- 来源文件；
- 条款定位；
- 官方URL；
- 本地归档哈希。

前端不得只展示LLM生成的政策摘要。

### 3.4 “数据与审核”

至少分为：

- 企业待填写；
- 企业已提供待审核；
- 已验证；
- 公开数据缺口；
- 建议海关预裁定；
- 审批/许可证待确认；
- 优惠资格待确认。

### 3.5 “AI政策助手”

AI入口可以保留，但调用链必须是：

```text
用户问题
  ↓
后端识别国家、日期、车型、路径
  ↓
查询规则、税率、审批和计算记录
  ↓
确定性Python计算
  ↓
AI解释已存储结果和来源
```

AI不得：

- 自行生成税率；
- 自行选择最终HS；
- 将CANDIDATE当VERIFIED；
- 绕过企业必填字段；
- 将项目优惠当成所有企业通用政策；
- 修改已验证数据。

## 4. 五路径前端决策流程

前端按以下顺序提问，不能让用户一开始随意选择结果。

### 4.1 路径1：CBU

问题：

```text
进口时是否已经是一辆完整、可作为整车申报的车辆？
```

如果是，进入CBU流程。

必填项：

- 进口日期；
- 原产国；
- 商业动力类型；
- 海关动力结构；
- 发动机燃料；
- 排量；
- 是否可外接充电；
- 车身类型；
- 驱动形式；
- 海关价值；
- AP类型和状态；
- FTA资格及证明。

### 4.2 路径2：整套CKD

问题：

```text
整套货物是否已取得MITI CKD AP，并被确认满足完整CKD定义？
```

只有用户上传或引用有效批准时才允许进入路线2。

必填项：

- CKD AP；
- 套件完整性确认；
- 完整CKD税号；
- 套件海关价值；
- 本地消费税价值；
- 本地销售价值；
- 项目批准消费税率或法定税率；
- 本地BEV或其他项目优惠批准。

### 4.3 路径3：分总成

问题：

```text
货物是否以发动机、变速箱、电池、电机、车身、底盘等分总成成组进口？
```

必填项：

- N205或适用审批；
- 各税务桶价值；
- 每个桶适用完整税号或CCU集合；
- 进口销售税；
- 零部件免税批准；
- 本地成车消费税和销售税输入。

### 4.4 路径4：CCU/零件级

适用于不能安全进入路线2或3的独立零件。

前端必须：

1. 获取CCU的`required_input_fields`；
2. 显示候选HS6及完整税号；
3. 要求用户显式选择映射；
4. 显示VERIFIED/CANDIDATE；
5. 未完成企业参数时禁用“正式计算”；
6. 允许“保存草稿”；
7. 对争议项显示“建议预裁定”。

### 4.5 路径5：混合KD

前端必须提供价值分配表：

| 字段 | 说明 |
|---|---|
| shipment_line_id | 企业装箱/发票行 |
| bucket_code | 8个税务桶之一 |
| customs_value | 该行分配价值 |
| selected_mapping | 税率映射 |
| approval_reference | 适用批准 |
| local_or_imported | 本地采购或进口 |

后端必须校验：

```text
每个shipment_line_id只能进入一个互斥税务桶
Σ分配价值 = 申报总价值
不存在重复mapping/bucket组合
本地采购价值不进入进口关税
批准免税只作用于批准覆盖的行
```

## 5. 前端状态模型

不要只用“成功/失败”。统一使用：

```typescript
type VerificationStatus =
  | "UNVERIFIED"
  | "CANDIDATE"
  | "VERIFIED"
  | "RULING_CONFIRMED";

type Completeness =
  | "COMPLETE"
  | "PARTIAL"
  | "BLOCKED";

type InputValueStatus =
  | "EMPTY"
  | "PROVIDED"
  | "VERIFIED"
  | "REJECTED";
```

展示规则：

| 状态 | 前端行为 |
|---|---|
| VERIFIED | 绿色，可用于计算 |
| RULING_CONFIRMED | 深绿色，显示预裁定编号 |
| CANDIDATE | 黄色，允许模拟但要求风险提示 |
| UNVERIFIED | 红色，阻止正式计算 |
| BLOCKED | 禁用结果排名，列出缺失字段 |
| PARTIAL | 显示模拟结果，不标记为可执行方案 |

## 6. 前端不能直接进入数据库

### 6.1 禁止方式

禁止在React/Vue/Next前端中出现：

```text
POSTGRES_PASSWORD
DATABASE_URL
Supabase service_role key
数据库管理员账号
任意SQL执行接口
```

即使以后使用Supabase，也不能把`service_role`密钥交给浏览器。

### 6.2 推荐方式

```text
Frontend
  ↓ access token
FastAPI
  ↓ server-side database role
PostgreSQL
```

数据库建议创建：

- `gais_api_read`：读取公开政策、规则、税率和来源视图；
- `gais_api_enterprise`：写入企业输入、草稿和证据引用；
- `gais_calculation`：写入计算及审计记录；
- `gais_data_reviewer`：审核和版本发布；
- 迁移账号仅在部署时使用。

前端用户角色和数据库角色不要一一直接映射；权限由后端业务服务控制。

## 7. 后端同事需要新增的API

建议统一前缀：

```text
/api/v1
```

### 7.1 国家首页

```http
GET /api/v1/countries/MY/overview?as_of=2026-07-29
```

返回：

```json
{
  "country": {"iso2": "MY", "name_cn": "马来西亚"},
  "as_of": "2026-07-29",
  "route_readiness": [],
  "policy_nodes": {
    "current": 0,
    "future_effective": 0,
    "expiring": 0
  },
  "open_missing_data": 0,
  "last_verified_at": "2026-07-29T00:00:00Z"
}
```

读取：

```text
ai.v_malaysia_five_route_readiness
rules.country_rule_card
rules.approval_matrix
audit.missing_data
```

### 7.2 五路径列表

```http
GET /api/v1/countries/MY/tax-routes?as_of=2026-07-29
```

读取：

```text
ai.v_malaysia_five_route_decision_current
```

### 7.3 路径判定

```http
POST /api/v1/countries/MY/tax-routes/resolve
```

请求：

```json
{
  "as_of": "2026-07-29",
  "shipment_state": "PARTS_OR_UNASSEMBLED",
  "ckd_ap_confirmed": false,
  "ckd_definition_confirmed": false,
  "n205_confirmed": true,
  "has_subassemblies": true,
  "has_individual_parts": true,
  "mixed_value_allocation": false
}
```

返回：

```json
{
  "selected_route_code": "ROUTE-MY-03-PARTS-SUBASSEMBLIES",
  "verification_status": "VERIFIED",
  "required_input_fields": [],
  "required_approvals": [],
  "fallback_route_code": "ROUTE-MY-04-PART-LEVEL",
  "source_clauses": []
}
```

路径判定必须由后端读取`decision_condition`执行，不能在前端复制一套业务规则。

### 7.4 CBU/CKD完整税号选项

```http
GET /api/v1/countries/MY/vehicle-tariffs
```

查询参数：

```text
as_of
route_code
origin_regime
agreement_code
hs6_code
powertrain
```

读取：

```text
ai.v_malaysia_vehicle_tariff_rates_current
```

返回的金额税率必须使用字符串，避免JavaScript浮点误差：

```json
{
  "national_tariff_code": "870380...",
  "import_duty_rate": "0.30000000",
  "sales_tax_rate": "0.10000000",
  "excise_duty_rate": null,
  "excise_treatment": "UNKNOWN",
  "verification_status": "CANDIDATE",
  "source": {
    "source_code": "...",
    "locator": "..."
  }
}
```

### 7.5 CCU目录

```http
GET /api/v1/ccus?country=MY&query=battery
GET /api/v1/ccus/{ccu_code}
GET /api/v1/ccus/{ccu_code}/tariff-options?as_of=2026-07-29
```

后端必须返回所有候选，不替用户选最终税号。

### 7.6 企业参数收集

```http
GET /api/v1/enterprise/part-ccu-links/{link_id}/inputs
PUT /api/v1/enterprise/part-ccu-links/{link_id}/inputs/{field_path}
DELETE /api/v1/enterprise/part-ccu-links/{link_id}/inputs/{field_path}
GET /api/v1/enterprise/part-ccu-links/{link_id}/completion
```

读取：

```text
enterprise.v_part_ccu_input_collection
enterprise.v_part_ccu_input_completion
```

写入只能调用：

```text
enterprise.set_part_ccu_input_value(...)
enterprise.clear_part_ccu_input_value(...)
```

前端不得直接更新`enterprise.part_ccu_input_value`。

写入示例：

```json
{
  "value_payload": "CONTINUOUS_RATED",
  "provided_by": "user-id",
  "evidence_refs": ["enterprise-file-id"],
  "notes": "来自供应商规格书第3页",
  "mark_verified": false
}
```

`UNKNOWN`、`PENDING`、`待确认`可以保存以便追踪，但不能通过必填门禁。

### 7.7 审批和优惠

```http
GET  /api/v1/countries/MY/requirements?route_code=...
POST /api/v1/projects/{project_id}/approvals
GET  /api/v1/projects/{project_id}/approval-readiness
```

企业批准字段必须包括：

- approval reference；
- authority；
- issue date；
- effective from/to；
- covered model；
- covered tariff codes/parts；
- approved rate或减免范围；
- localization/vendor/value-added条件；
- evidence file reference；
- verification status。

### 7.8 五路径计算

```http
POST /api/v1/calculations/malaysia/preview
POST /api/v1/calculations/malaysia/run
GET  /api/v1/calculations/{run_id}
GET  /api/v1/calculations/{run_id}/trace
GET  /api/v1/calculations/{run_id}/missing-data
```

`preview`不写入正式审计记录；`run`必须创建：

```text
enterprise.scenario_input
enterprise.input_snapshot
calc.calculation_run
calc.calculation_line
audit.decision_trace
audit.missing_data
ai.llm_view_item
```

正式请求必须带：

```http
Idempotency-Key: <uuid>
```

防止用户双击造成重复计算记录。

### 7.9 政策与证据

```http
GET /api/v1/countries/MY/rules
GET /api/v1/rules/{rule_code}
GET /api/v1/sources/{source_code}
GET /api/v1/sources/{source_code}/clauses
```

下载归档文件必须使用后端生成的短时签名URL，不直接暴露存储管理员密钥。

## 8. 计算请求原则

前端只提交：

- 用户事实；
- 企业输入；
- 用户显式选择的映射ID；
- 审批引用；
- 计算日期；
- 需要比较的制度；
- 收入和成本口径。

前端不提交：

- 自己计算的税率；
- 自己推导的法定优惠；
- 自己选择的最终HS结论；
- 未经后端读取的政策版本。

后端在每次计算时读取当日有效版本，并创建不可变输入快照。

## 9. CBU与KD结果页

结果页建议分成四层。

### 9.1 领导摘要

```text
推荐路径
CBU总税负率
KD总税负率
税后成本差
利润差
优惠到期后敏感性
结果完整度
需要管理层确认事项
```

### 9.2 路径比较

| 指标 | CBU | 整套CKD | 分总成 | CCU级 | 混合KD |
|---|---:|---:|---:|---:|---:|
| 进口关税 | | | | | |
| 进口销售税 | | | | | |
| 本地成车消费税 | 不适用 | | | | |
| 本地成车销售税 | 不适用 | | | | |
| 总税额 | | | | | |
| 有效税率 | | | | | |
| 税后成本 | | | | | |
| 毛利润 | | | | | |
| 完整度 | | | | | |

不同模式必须使用统一分母，否则不能比较综合税率。

### 9.3 计算明细

显示每一步：

- 计税基础；
- 税率；
- 税额；
- 使用的规则；
- 使用的税率映射；
- 来源条款；
- 是否来自企业批准。

### 9.4 风险和缺失

必须在结果旁边展示：

- GRI 2(a)；
- 8708排除；
- AP监管；
- FTA资格；
- 企业必填缺失；
- 预裁定建议；
- 项目优惠到期；
- CANDIDATE映射。

## 10. 推荐前端页面路由

```text
/
/countries
/countries/MY
/decision/new
/decision/{project_id}/route
/decision/{project_id}/inputs
/decision/{project_id}/approvals
/decision/{project_id}/comparison
/calculations/{run_id}
/policies
/policies/{rule_code}
/sources/{source_code}
/data-review
/data-review/enterprise-inputs
/data-review/missing-data
/ai-assistant
```

## 11. 接入顺序

### 第一批：只读接入

1. `/health`；
2. 国家概览；
3. 五路径列表和就绪度；
4. 规则、来源和税率详情；
5. 首页动态指标。

### 第二批：决策向导

1. 路径判定；
2. 企业参数表单；
3. AP及优惠批准；
4. 税号候选显式选择；
5. 完成度门禁。

### 第三批：计算闭环

1. 五路径Preview；
2. 正式Run；
3. CBU/KD利润比较；
4. Calculation Line；
5. Decision Trace和Missing Data。

### 第四批：AI解释

1. AI只读取后端整理的LLM View；
2. 回答附`rule_code`、`mapping_code`和来源；
3. AI建议与正式结果分开展示；
4. AI输出不得改变计算记录。

## 12. 本地开发

数据库：

```powershell
docker compose up -d postgres
.\scripts\db-run-malaysia-five-route-tax-model.ps1
```

后端：

```powershell
cd backend
$env:GAIS_DATABASE_URL="postgresql+psycopg://gais:<password>@127.0.0.1:5432/global_auto"
uvicorn app.main:app --reload
```

当前API文档：

```text
http://127.0.0.1:8000/docs
```

前端环境变量只保存API地址：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

不要保存数据库连接串。

## 13. 后端上线前检查

- [ ] 新API使用`/api/v1`版本前缀；
- [ ] 配置允许的CORS域名，不使用生产环境`*`；
- [ ] 所有金额和税率以字符串传输；
- [ ] 所有日期使用ISO 8601；
- [ ] 所有查询按`as_of`筛选有效版本；
- [ ] CANDIDATE和UNVERIFIED不能静默变成VERIFIED；
- [ ] 正式计算必须创建输入快照；
- [ ] 正式计算支持Idempotency-Key；
- [ ] FTA不合格自动回退MFN并记录原因；
- [ ] 企业优惠缺批准时回退法定税率；
- [ ] 企业必填字段不完整时返回BLOCKED；
- [ ] 计算响应包含规则、税率和来源引用；
- [ ] AI没有数据库写权限；
- [ ] 浏览器中不存在数据库凭证；
- [ ] 审计记录不保存LLM隐藏思考链。

## 14. 前端验收标准

输入：

```text
Malaysia
2026
China origin
BEV / PHEV / ICE
CBU或某种KD货物状态
车型及企业参数
审批和原产地证明
成本、售价及本地组装输入
```

输出至少包括：

```text
判定路径及判定依据
适用完整税号或候选
MFN/ACFTA/RCEP税率
进口关税
进口销售税
本地成车消费税
本地成车销售税
综合税负率
税后成本
利润和利润率
与CBU/KD基准的差异
规则、税号和来源
风险标签
缺失企业数据
审批状态
计算快照和审计编号
```

只有当`completeness=COMPLETE`且关键映射和批准达到允许状态时，前端才能显示
“可供正式决策使用”。其他结果必须显示为模拟或待确认。
