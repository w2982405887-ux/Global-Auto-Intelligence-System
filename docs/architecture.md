# Phase 1 架构

## 分层

```text
外部官方来源/企业输入
        ↓
evidence：原始文件、网页快照、条款
        ↓
rules + customs：原子规则、CCU、HS 候选、国家税号映射
        ↓
enterprise：车型、料号、BOM、场景输入快照
        ↓
calc：确定性计算运行与逐行税额
        ↓
audit + ai：可审计判断、缺失数据、LLM 可读视图
```

## Schema 职责

| Schema | 职责 |
|---|---|
| `ref` | 国家、主管机关、协定、稳定字典 |
| `evidence` | 来源文件、具体条款、归档对象 |
| `rules` | 国家规则、审批/优惠要求、场景模板 |
| `customs` | CCU、HS6 候选、国家完整税号映射 |
| `enterprise` | 车型、企业料号、BOM、用户输入及快照 |
| `calc` | 计算运行和逐税种计算行 |
| `ai` | 允许 LLM 读取的最小化视图项目 |
| `audit` | 判断轨迹、缺失数据、人工复核 |

## 关键约束

### CCU 与企业料号解耦

`enterprise.enterprise_part` 不保存最终税号。它通过
`enterprise.enterprise_part_ccu_link` 连接一个 CCU，并保留置信度、审核状态和有效期。

### HS 候选与国家税号解耦

`customs.ccu_candidate_hs` 保存 CCU 的 1—3 个 HS6 候选；
`customs.tariff_mapping` 再把候选映射到 PDK 版本下的马来西亚完整税号及原产地制度。
`customs.ccu_risk_tag` 则以三条独立维度记录 GRI 2(a)、8708 排除和 AP 监管风险。

### 一行一个制度

MFN、RCEP、ACFTA 等不能做成横向税率列。每条 `tariff_mapping` 只代表一个：

```text
CCU + HS 候选 + 国家完整税号 + 原产地制度 + 有效期
```

### 时间语义

所有有效期统一为左闭右开区间：

```text
[effective_from, effective_to)
```

`effective_to IS NULL` 表示尚无已知终止日期。修订时插入新记录并关闭旧记录，禁止覆盖历史。

### 规则执行

`condition_expression` 和 `calculation_expression` 必须符合
`calculation_dsl.schema.json` 所定义的有限 AST。执行器只识别白名单操作符，不调用
`eval`，不执行 SQL、Python 或 LLM 返回的自由文本。

### 审计轨迹

`audit.decision_trace` 保存输入记录、规则、来源、显式业务理由和结果。它不是模型隐藏思考链，
也不保存提示词内部推理。
