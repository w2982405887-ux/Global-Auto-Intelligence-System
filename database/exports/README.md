# 数据库导出与恢复

导出时间：2026-08-25；PostgreSQL 16；源数据库：`global_auto`。

## 交接文件

| 文件 | 用途 | GitHub |
|---|---|---|
| `schema/global_auto_schema_2026-08-25.sql` | 纯结构快照（无owner/privilege） | 可提交 |
| `full/global_auto_full_2026-08-25.dump` | 完整custom-format备份 | 禁止提交 |
| `full/global_auto_full_2026-08-25.list` | `pg_restore --list`清单 | 禁止提交 |

SHA-256：

```text
276101C9FAB30351C9818094EC81ED1EA60886646E90EF5EE3522B44225A7A68  schema/global_auto_schema_2026-08-25.sql
45768BDDD453E92E62ED711001A988E5FCD5E9837204574D40384DFFAA51F610  full/global_auto_full_2026-08-25.dump
6906A821CEA11866A93B0A78F3E51E897551AE2BDA9D10B63F79FE596F619DE3  full/global_auto_full_2026-08-25.list
```

结构快照含11个schema和55条 `CREATE TABLE`。完整dump已恢复到临时数据库并通过验证，恢复后可见64个非系统table/view对象。

## 校验

```powershell
Get-FileHash .\database\exports\schema\global_auto_schema_2026-08-25.sql -Algorithm SHA256
Get-FileHash .\database\exports\full\global_auto_full_2026-08-25.dump -Algorithm SHA256
```

## 恢复完整备份（只恢复到新测试库）

```powershell
cd "C:\Users\w2982\Documents\Codex\2026-07-27\kd-hs6\Global-Auto-Intelligence-System"
docker compose up -d postgres
docker cp .\database\exports\full\global_auto_full_2026-08-25.dump gais-postgres:/tmp/restore.dump
docker compose exec -T postgres sh -lc 'createdb -U "$POSTGRES_USER" global_auto_restore_test'
docker compose exec -T postgres sh -lc 'pg_restore -U "$POSTGRES_USER" -d global_auto_restore_test /tmp/restore.dump'
```

不要恢复到正在运行的 `global_auto`。正式迁移前先在测试库运行应用测试和数据抽查。

## 重要边界

- 完整dump包含账号、聊天记录和业务数据，必须加密保存；
- `.env`、数据库密码、认证密钥、模型/搜索Key不在本目录交接；
- `storage/evidence`、`storage/assistant_uploads`不在PostgreSQL dump中，应单独加密归档；
- 日常重建仍以 `database/migrations`、`database/seeds`、`database/reference_exports` 为版本化来源，结构快照用于审计和快速比对。
