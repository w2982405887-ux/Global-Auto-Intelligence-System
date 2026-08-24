# 企业CCU技术参数延迟采集流程

## 适用原则

- 公共政策、PDK税号和候选归类研究可以先进行。
- 企业技术参数不预填、不猜测，也不使用建议值代替企业事实。
- 企业料号与CCU建立关联时，数据库自动生成该CCU的全部参数空位。
- 参数可以逐条保存；`UNKNOWN`、`待确认`等未决值可以留作审计，但不计入完成。
- 创建不可变输入快照、执行最终归类或税务计算前，所有“使用时必填”参数必须完成。

## 数据所在位置

### 字段定义

`customs.ccu_input_requirement`

一行代表一个CCU技术参数定义，包含：

- 字段路径；
- 中文名称；
- 数据类型；
- 单位；
- 允许值；
- 数据责任人；
- 是否使用时必填；
- 建议值。

`suggested_value`只用于提示，不会复制到企业事实记录。

### 企业填写值

`enterprise.part_ccu_input_value`

一行代表一个企业料号与CCU关联下的一个参数空位。状态为：

- `EMPTY`：尚未填写；
- `PROVIDED`：企业已经提供；
- `VERIFIED`：已经审核；
- `REJECTED`：提供值被拒绝，需要重新填写。

## 使用流程

### 1. 建立企业料号和CCU关联

向`enterprise.enterprise_part_ccu_link`插入记录后，数据库触发器会自动生成参数空位。

### 2. 查看待填字段

```sql
SELECT *
FROM enterprise.v_part_ccu_input_collection
WHERE part_ccu_link_id = '<PART_CCU_LINK_UUID>'
ORDER BY display_order;
```

### 3. 查看完成度

```sql
SELECT *
FROM enterprise.v_part_ccu_input_completion
WHERE part_ccu_link_id = '<PART_CCU_LINK_UUID>';
```

### 4. 填写一个参数

```sql
SELECT enterprise.set_part_ccu_input_value(
  '<PART_CCU_LINK_UUID>',
  'part.rated_output_kw',
  '150'::jsonb,
  '填写人姓名或工号',
  '["电机规格书-DWG-001"]'::jsonb,
  '连续额定输出功率'
);
```

JSON值类型必须与字段定义一致：

- 文本和枚举：`'"8703"'::jsonb`
- 数字：`'150'::jsonb`
- 布尔值：`'true'::jsonb`或`'false'::jsonb`
- JSON对象：`'{"key":"value"}'::jsonb`

### 5. 审核时写入已验证值

```sql
SELECT enterprise.set_part_ccu_input_value(
  '<PART_CCU_LINK_UUID>',
  'part.current_type',
  '"MULTI_PHASE_AC"'::jsonb,
  '企业工程填写人',
  '["电机规格书-DWG-001"]'::jsonb,
  '铭牌和规格书一致',
  true,
  '关务审核人'
);
```

### 6. 清空错误值

```sql
SELECT enterprise.clear_part_ccu_input_value(
  '<PART_CCU_LINK_UUID>',
  'part.rated_output_kw'
);
```

清空后，该字段立即恢复为必填缺口。

### 7. 使用前检查

单个企业料号与CCU关联：

```sql
SELECT enterprise.assert_part_ccu_inputs_ready(
  '<PART_CCU_LINK_UUID>',
  DATE '2026-01-01'
);
```

整车BOM：

```sql
SELECT enterprise.assert_bom_inputs_ready(
  '<BOM_VERSION_UUID>',
  DATE '2026-01-01'
);
```

如果存在缺失或未决值，函数会报错并列出缺失字段。系统在创建
`enterprise.input_snapshot`时也会自动执行BOM级检查。

## 当前首批范围

- 9个CCU；
- 83个参数定义；
- 82个使用时必填参数；
- 1个可选参数；
- 当前没有录入任何真实企业技术值。
