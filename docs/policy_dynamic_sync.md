# 特殊优惠政策动态与定时更新接口约定

## 当前首页政策动态的口径

首页“政策动态”只展示 `rules.automotive_incentive_program` 中马来西亚（MY）和越南（VN）的特殊政策，包括：

- FTA/原产地优惠；
- CBU/CKD 进口关税减免；
- BEV、HEV、PHEV 等动力类型优惠；
- 本地化、零部件制造和产量门槛激励；
- 首次登记费、特别消费税等生命周期优惠；
- 项目审批型、配额型优惠。

普通 MFN/FTA 税率明细仍然属于税率表，不直接混入首页政策动态；CBU/CKD 测算页面会根据条件单独调用这些税率。

## 数据流

```text
OpenClaw / Codex 定时搜索
        ↓
原始文件与官方链接
        ↓
evidence.source_document / evidence.source_clause
        ↓
rules.automotive_incentive_program（CANDIDATE）
        ↓ 人工或规则核验
VERIFIED / RULING_CONFIRMED
        ↓
首页特殊优惠政策动态 + CBU/CKD 条件匹配
```

模型或搜索任务不得直接修改已核验政策，也不得直接把搜索结果变成确定税率。新记录默认写入 `CANDIDATE`，并保留原文、译文、来源文件、条款定位和抓取时间。

## 定时任务预留

服务器部署时可由以下任一调度器触发同一个同步任务：

- OpenClaw Gateway 的定时任务；
- Linux `systemd timer` 或 `cron`；
- Windows Task Scheduler；
- 独立 Codex/Agent worker。

调度器只负责触发同步 worker，不直接连接 PostgreSQL。worker 应调用后端受保护的内部同步接口，提交规范化政策草稿，并使用幂等键：

```text
country_iso2 + program_code + effective_from + source.content_sha256
```

建议同步任务分为四步：

1. 发现官方公告、法规、税则附件和主管机关页面；
2. 下载并保存原始文件，计算 `content_sha256`；
3. 抽取政策条件、优惠效果、有效期和适用路径，生成 `CANDIDATE` 草稿；
4. 对变更、冲突和高影响政策进入人工核验队列。

## 安全边界

- 不给 OpenClaw/Codex 直接数据库账号；
- 不允许模型执行任意 SQL、shell 或文件删除；
- 同步接口只允许写入候选政策和证据，不允许删除历史版本；
- 所有版本采用生效日期和记录状态控制，历史记录只追加不覆盖；
- 只有人工核验或受控规则才能将 `CANDIDATE` 改为 `VERIFIED`。

