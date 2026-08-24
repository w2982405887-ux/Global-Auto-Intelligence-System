# PostgreSQL 本地启动

## 前置条件

当前电脑需先安装并启动 Docker Desktop。安装完成后，在 PowerShell 中确认：

```powershell
docker --version
docker compose version
docker info
```

## 第一次创建数据库

在项目目录执行：

```powershell
Copy-Item .env.postgres.example .env
notepad .env
docker compose up -d postgres
docker compose ps
docker compose exec postgres pg_isready -U gais -d global_auto
```

`.env` 中的密码仅用于本地开发，不要提交到 Git。

## 建表

```powershell
.\scripts\db-migrate.ps1
.\scripts\db-verify.ps1
```

成功时应看到八个业务 Schema 及其表数量。

## 录入马来西亚最小 Demo

```powershell
.\scripts\db-seed-malaysia.ps1
.\scripts\db-verify-malaysia.ps1
```

首批数据来自 PDK 2025、MITI AP 官方页面和 JKDM HS Explorer。动力电池包的
HS6 `850760` 只作为候选；在 HS Explorer 核验马来西亚完整税号和税率之前，
系统会显示 `NULL` 并生成 P0 缺失项。这是预期结果。

## 连接数据库

进入容器内的 `psql`：

```powershell
docker compose exec postgres psql -U gais -d global_auto
```

常用只读命令：

```sql
\dn
\dt evidence.*
\dt rules.*
\dt customs.*
\dt calc.*
SELECT current_database(), current_user, version();
```

退出：

```sql
\q
```

## 停止与重新启动

```powershell
docker compose stop
docker compose start
```

`docker compose down` 会删除容器但保留命名数据卷。
不要运行 `docker compose down -v`，除非明确要删除整个本地数据库。
