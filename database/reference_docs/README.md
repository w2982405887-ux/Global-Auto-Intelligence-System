# 外部研究文档目录

这里用于存放未纳入 Git 的官方附件（例如越南 ACFTA、ATIGA、RCEP 的 Word/PDF 税率附件）。
附件可能包含版权或内部研究资料，默认不要提交到仓库。

推荐目录结构：

```text
database/reference_docs/vietnam_fta/
├── china-asean/   # ACFTA 文件
├── asean/         # ATIGA 文件
└── rcep/          # RCEP 文件
```

提取脚本默认读取上述仓库内相对目录。如果附件放在其他位置，在运行前设置：

```powershell
$env:GAIS_VIETNAM_FTA_DOCS_ROOT = "D:\research\vietnam_fta"
python database/scripts/extract_vietnam_fta_major_part_rates.py
python database/scripts/extract_vietnam_fta_8703_rates.py

$env:GAIS_RCEP_DOCS_DIR = "D:\research\vietnam_fta\rcep"
python database/scripts/inspect_rcep_doc_headers.py
```

脚本不会自动扫描用户 Downloads、桌面或其他不可迁移的个人目录。
