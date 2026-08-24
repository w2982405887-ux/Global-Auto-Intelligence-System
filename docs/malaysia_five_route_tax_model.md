# 马来西亚汽车 CBU/KD 五路径税务决策模型

数据基准日：2026-07-29  
适用范围：马来西亚、8703乘用车、中国原产优先比较 MFN / ACFTA / RCEP  
核心目标：计算 CBU 与不同 KD 路径的综合税负及税后成本差，而不是建设逐料号报关系统。

## 一、五路径必须按顺序判断

系统必须从路线1开始。只有上一条路线不符合事实或审批条件时，才能进入下一条。

### 路线1：CBU整车进口

适用条件：

- 货物进口时已经是完整车辆；
- 使用整车完整税号，不拆分零件；
- 已确认车辆用途、动力技术、发动机类型、是否可外接充电、排量、车身及驱动形式；
- 已取得适用的 MITI AP、年度配额或车型资格；
- 若申请FTA优惠，已取得该票货物的原产地证明并满足直接运输等条件。

计算链：

```text
进口关税 = 海关价值 × 进口关税率
消费税基础 = 海关价值 + 进口关税
消费税 = 消费税基础 × 消费税率
进口销售税基础 = 海关价值 + 进口关税 + 消费税
进口销售税 = 进口销售税基础 × 销售税率
CBU进口税合计 = 进口关税 + 消费税 + 进口销售税
```

税率选择：

1. 以 PDK 2025 完整10位税号取得MFN关税；
2. 中国原产可分别测试 ACFTA、RCEP；
3. FTA不合格或缺少该票证明时回退MFN；
4. 消费税按 P.U. (A) 389/2025 对应完整税号；
5. 销售税按当前适用税则和税令处理。

重要政策边界：

- CBU BEV 的普遍进口关税和消费税特别豁免已于2025-12-31结束；
- 自2026-07-01起，CBU EV适用MITI公布的最低CIF RM200,000和最低功率180 kW条件；
- 不得把BEV优惠复制给HEV、PHEV或EREV；
- EREV必须按实际技术结构判断是否落入可外接充电的混合动力税号。

### 路线2：整套CKD车辆税号进口

适用条件：

- 同一套货物及进口安排满足海关/主管机关的CKD定义；
- 取得 MITI CKD AP；
- 能落入 PDK 2025 的完整 CKD 车辆税号；
- 货物不是未获CKD认可的零散部件或分总成。

进口环节：

```text
CKD套件进口关税 = CKD套件海关价值 × 对应完整税号关税率
CKD套件进口销售税 = 0
```

PDK 2025中共有167条8703 CKD完整税号。它们依据
P.U. (A) 171/2025列入销售税豁免，但进口关税并非统一为0；已取得的官方
PDK结果显示税率范围为0%至35%。CKD套件进口时不把整车消费税自动计入套件，
消费税在本地组装成车移出制造场所时按成车规则处理。

本地成车环节：

```text
本地成车消费税 = 经批准/依法确定的本地消费税价值 × 法定或项目批准税率
本地成车销售税 = 依法确定的本地销售价值 × 适用销售税率
路线2总税负 = 套件进口关税 + 套件进口销售税
              + 本地成车消费税 + 本地成车销售税
```

本地消费税价值与本地销售价值是两个依法确定的输入，系统不得用CIF或成本值
擅自替代。项目优惠也不得从“本地化率”自动推导，必须读取企业批准函。

### 路线3：分总成/税务桶进口

适用条件：

- 进口货物没有作为完整CKD套件获批；
- 以发动机、变速箱、电池、电机、电控、车身、底盘等分总成或成组零件进口；
- 按 MITI N205 Parts/Sub-Assemblies 等适用审批路线办理；
- 进口价值可以稳定分配到税务桶。

八个税务桶：

1. 完整CKD套件；
2. ICE动力总成；
3. EV动力总成；
4. 车身与底盘；
5. 普通进口零件；
6. 获批免税进口件；
7. 本地采购件；
8. 特殊监管或贸易救济件。

进口计算：

```text
税务桶进口关税 = Σ(桶内进口价值 × 该桶适用关税率)
税务桶进口销售税 = Σ(依法确定的进口销售税基础 × 适用税率)
```

之后仍需叠加本地组装成车的消费税和销售税。零件免税仅在取得有效项目/税务
批准并且该零件、用途、数量、期限都在批准范围内时适用。

### 路线4：海关归类单元/零件级进口

适用条件：

- 无法可靠归入路线2或路线3；
- 某一零件价值高、税率非零、存在归类争议、进口监管、原产地疑问或贸易救济；
- 企业技术参数足以支持完整税号选择。

研究粒度仍然是CCU，不是企业物理料号。每个企业料号先挂接CCU，再由CCU保留
1至3个候选HS6和马来西亚完整税号候选。

企业技术资料缺失时：

- 保留多个候选；
- 标记CANDIDATE或UNVERIFIED；
- 税率计算BLOCK；
- 必要时申请海关预裁定；
- 不得由AI自行决定最终税号。

### 路线5：混合KD

适用条件：

- 一部分货物以完整CKD套件申报；
- 一部分按分总成、普通零件或独立CCU进口；
- 另有本地采购件或项目免税件。

系统必须先把总价值分配到互斥税务桶，并使用
`shipment_id + line_id + bucket_code`防止同一价值重复计税。

```text
混合KD总税负
= 完整CKD套件进口税
+ 分总成/零件进口税
+ 本地成车消费税
+ 本地成车销售税
- 有批准依据的减免
```

若某一价值无法唯一分配，系统必须停止计算并要求企业补充装箱清单、发票或
批准清单。

## 二、已固化的官方公共数据

### 整车税率

- PDK 2025：471条8703完整车辆税号；
- 其中CBU 304条、CKD 167条；
- ACFTA当前结果：471条完整税率记录；
- RCEP当前结果：647条完整税率记录；
- 共1,589条按制度独立保存的税率记录；
- 所有1,589条均有公开进口关税率；
- PDK 2025的253条记录有公开消费税率；
- 其余218条保持空值：167条CKD为进口环节不征成车消费税，51条CBU结果
  未显示消费税，系统保持UNKNOWN并阻止无依据计算。

### 已有CCU数据的复用

- 现有60个活跃海关归类单元直接用于路线3、4和5；
- 其中58个CCU已挂接346条MFN/FTA完整税率映射，公开关税缺失数为0；
- `CCU-ENGINE-BLOCK-OR-HEAD`和`CCU-ENGINE-FUEL-INJECTOR`各自已有
  840991/840999候选HS6，但马来西亚完整税号仍受点火方式、母发动机类别和
  具体部件类型影响，因此保留CANDIDATE并在使用时要求企业参数；
- 路线3至5复用既有`customs.tariff_mapping`，不把零件税率重复写入整车税率表。

FTA税率行保留其自身完整税号。ACFTA、RCEP与PDK的国家子目结构不同时，
不得强行生成虚假的一对一对应；计算消费税前必须完成PDK关联。

### ACFTA与RCEP资格

8703适用的主要原产地门槛按当前官方规则记录为RVC40。ACFTA使用Form E；
RCEP使用Form RCEP或经批准出口商声明。优惠资格必须按票确认，并保留直接
运输或中转证明。缺失时自动回退MFN，不得把FTA税率当作中国原产货物的默认税率。

### SST而非VAT

马来西亚当前车辆货物链使用销售税和消费税，不存在需要额外叠加的独立VAT/GST。
服务税仅在另有应税服务进入成本模型时单独处理，不得加到所有车辆进口场景。

### AP、配额和项目优惠

- CBU：N180或适用的Franchise AP路径；年度AP数量以企业获批配额为准；
- 完整CKD：MITI CKD AP并满足CKD定义；
- 分总成：不满足完整CKD时转入N205；
- 零件：逐完整税号检查当前进口禁止/监管清单；
- 本地BEV优惠：以有效至2027-12-31的政策边界和企业实际批准为门禁；
- 汽车定制化优惠、本地化关联优惠及零部件免税：均以企业项目批准函为准。

公开文件没有提供一个可供所有企业直接套用的“本地化率→消费税优惠率”公式。
系统因此只保存政策边界，不预填企业优惠率，也不把“满足本地化率”自动解释
为已取得减免。

## 三、必须由企业在使用时填写

### 所有模式共同字段

- 计算日期、原产国、贸易制度；
- 车辆用途、座位数、动力技术结构；
- 发动机燃料和排量；
- 是否可外接充电；
- 车身、驱动形式及其他税号限定条件；
- 海关价值、币种、运保费口径；
- 该票原产地证明及直接运输证明。

### CBU额外字段

- 完整10位税号确认；
- AP类型、车型批准和年度配额；
- 51条消费税未公开显示税号中的主管机关确认或预裁定；
- CBU EV的CIF、最大功率及适用资格。

### CKD/KD额外字段

- CKD AP或N205批准；
- MITI/海关对套件状态的确认；
- 套件、分总成、零件和本地采购之间的价值分配；
- 本地制造许可或合同组装安排；
- 本地消费税价值；
- 本地销售税价值；
- 项目批准消费税率或减免率；
- 本地BEV税务批准；
- 零件免税批准清单、有效期、数量和用途；
- 本地化率只作为项目条件事实，不直接生成优惠率。

## 四、更新机制

以下变化必须新增版本，不覆盖历史：

- 新PDK或税则修订；
- ACFTA/RCEP年度或阶段税率更新；
- Excise Duties Order及其修订；
- Sales Tax税率、豁免和销售价值规则；
- Customs Prohibition of Imports Order；
- MITI AP政策、车型条件和年度配额规则；
- MOF/MIDA的EV与汽车定制化激励；
- 企业项目批准函、优惠率、有效期和批准清单。

每次更新必须保存：

```text
effective_from / effective_to / version / record_status
source_document / source_clause / authority / publication_date
verification_status / verified_at
```

## 五、官方来源

- [JKDM HS Explorer](https://ezhs.customs.gov.my/)
- [Sales Tax (Goods Exempted from Sales Tax) Order 2025, P.U. (A) 171/2025](https://pub-359af8e1f79c472292a7e44ec60f3027.r2.dev/SST%20Orders/3-PUA%20171%20(2025).pdf)
- [Sales Tax (Rate of Tax) Order 2025, P.U. (A) 170/2025](https://pub-359af8e1f79c472292a7e44ec60f3027.r2.dev/SST%20Orders/1-PUA%20170_2025.pdf)
- [Sales Tax Determination of Sale Value Regulations 2018](https://mysst.customs.gov.my/wp-content/uploads/2025/03/Sales-Tax-Determination-Of-Sale-Value-Of-Taxable-Goods-Regulations-2018.pdf)
- [JKDM MySST Business FAQ](https://mysst.customs.gov.my/faq-business/)
- [Excise Duties Order 2025, P.U. (A) 389/2025](https://www.customs.gov.my/images/06-prosedur/eksais/perintah/PUA389_2025.pdf)
- [Excise Duties (Payment of Duty) Order 2026, P.U. (A) 44/2026](https://www.customs.gov.my/images/06-prosedur/eksais/perintah/PUA%2044_2026.pdf)
- [Local Manufactured Goods Excise Valuation Regulations 2019, P.U. (A) 402/2019](https://www.customs.gov.my/images/06-prosedur/eksais/peraturan/P.U.A402-peraturan-eksais-penentuan-nilai-barang-yang-dikilangkan-secara-tempatan.pdf)
- [MITI CKD AP notice](https://www.miti.gov.my/miti/resources/Approve%20Permit/AP%20Announcement/NOTIS_MENGENAI_PERMOHONAN_LESEN_IMPORT_%28AP%29_COMPLETELY_KNOCKED_DOWN_%28CKD%29_SUSULAN_PENGUATKUASAAN_PERINTAH_KASTAM_1988_%28LATEST%29.pdf)
- [MITI N205 Parts/Sub-Assemblies](https://www.miti.gov.my/miti/resources/Approve%20Permit/Motor%20vehicle/FLOW_CHART_FOR_APPLICATION_AP_TYPE_%28INQ%29_%E2%80%93_OTHER_VEHICLE_PERMANENT_IMPORT_%E2%80%93_PARTS_SUB-ASSEMBLIES.pdf)
- [MITI N180 CBU](https://www.miti.gov.my/miti/resources/Approve%20Permit/Motor%20vehicle/11_OTHER_VEHICLE_PERMANENT_IMPORT_%E2%80%93_COMPLETELY_BUILD_UP_%28CBU%29.pdf)
- [MITI Franchise AP Policy 2026](https://www.miti.gov.my/miti/resources/Approve%20Permit/Franchise%20AP/DASAR_AP_FRANCAIS_2026_2.pdf)
- [MITI CBU EV conditions, 6 May 2026](https://www.miti.gov.my/miti/resources/Media%20Release/SIARAN_MEDIA_PENAMATAN_PENGECUALIAN_KHAS_6_Mei_2026_edited.pdf)
- [MOF Budget 2023 EV tax measures](https://belanjawan.mof.gov.my/pdf/belanjawan2023/ucapan/tax-measure.pdf)
- [MIDA Investment Performance Report 2025](https://www.mida.gov.my/wp-content/uploads/2026/03/MIDA_IPR.2025.pdf)
- [MIDA component import-duty/sales-tax exemption guide](https://www.mida.gov.my/wp-content/uploads/2020/12/20200804164306_GD_PC_RawMaterials_29072020.pdf)
- [MITI Rules of Origin portal](https://www.miti.gov.my/index.php/pages/view/3911)
- [JKDM Rules of Origin FAQ](https://www.customs.gov.my/ms/perniagaan/fasilitasi/rules-of-origin-roo/faq-rules-of-origin-roo)
- [JKDM current Prohibitions of Imports page](https://www.customs.gov.my/en/business/import-export/import/prohibitions-of-imports)

## 六、一键执行

在项目根目录运行：

```powershell
.\scripts\db-run-malaysia-five-route-tax-model.ps1
```

该命令依次启动PostgreSQL、执行幂等迁移、写入官方数据并运行强制验证。
