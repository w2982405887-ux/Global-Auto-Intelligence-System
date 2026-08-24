BEGIN;

WITH requirement_rows (
  ccu_code,
  field_path,
  field_name_cn,
  required_at_use,
  value_type,
  unit,
  suggested_value,
  allowed_values,
  data_owner,
  display_order
) AS (
  VALUES
    ($v$CCU-TRACTION-MOTOR$v$,$v$part.current_type$v$,$v$电机电流/相制式$v$,true,$v$ENUM$v$,NULL,NULL,$j$["MULTI_PHASE_AC","SINGLE_PHASE_AC","DC","OTHER"]$j$::jsonb,$v$企业工程$v$,1),
    ($v$CCU-TRACTION-MOTOR$v$,$v$part.rated_output_kw$v$,$v$连续额定输出功率$v$,true,$v$NUMBER$v$,$v$kW$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,2),
    ($v$CCU-TRACTION-MOTOR$v$,$v$part.output_power_basis$v$,$v$输出功率口径$v$,true,$v$ENUM$v$,NULL,$j$"CONTINUOUS_RATED"$j$::jsonb,$j$["CONTINUOUS_RATED","MAXIMUM_30MIN","PEAK","UNKNOWN"]$j$::jsonb,$v$企业工程$v$,3),
    ($v$CCU-TRACTION-MOTOR$v$,$v$part.primary_function$v$,$v$主要功能$v$,true,$v$ENUM$v$,NULL,$j$"TRACTION_MOTOR"$j$::jsonb,$j$["TRACTION_MOTOR","MOTOR_GENERATOR","INTEGRATED_EDRIVE","OTHER"]$j$::jsonb,$v$企业工程$v$,4),
    ($v$CCU-TRACTION-MOTOR$v$,$v$part.integrated_gearbox$v$,$v$是否集成减速器/齿轮箱$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,5),
    ($v$CCU-TRACTION-MOTOR$v$,$v$part.integrated_inverter$v$,$v$是否集成逆变器$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,6),
    ($v$CCU-TRACTION-MOTOR$v$,$v$vehicle.chapter$v$,$v$适用车辆章$v$,true,$v$TEXT$v$,NULL,$j$"87"$j$::jsonb,$j$[]$j$::jsonb,$v$企业工程$v$,7),
    ($v$CCU-TRACTION-MOTOR$v$,$v$vehicle.intended_heading$v$,$v$目标整车品目$v$,true,$v$ENUM$v$,NULL,$j$"8703"$j$::jsonb,$j$["8701","8702","8703","8704","8705","OTHER"]$j$::jsonb,$v$企业工程$v$,8),
    ($v$CCU-TRACTION-MOTOR$v$,$v$shipment.assembly_state$v$,$v$进口呈验状态$v$,true,$v$ENUM$v$,NULL,$j$"COMPLETE"$j$::jsonb,$j$["COMPLETE","INCOMPLETE","UNASSEMBLED","DISASSEMBLED","PARTIAL_SET","UNKNOWN"]$j$::jsonb,$v$物流包装$v$,9),
    ($v$CCU-TRACTION-INVERTER$v$,$v$part.primary_function$v$,$v$主要功能$v$,true,$v$ENUM$v$,NULL,$j$"DC_TO_CONTROLLED_MOTOR_CURRENT"$j$::jsonb,$j$["DC_TO_CONTROLLED_MOTOR_CURRENT","AC_TO_DC_RECTIFICATION","DC_TO_DC_CONVERSION","MULTIFUNCTION"]$j$::jsonb,$v$企业工程$v$,1),
    ($v$CCU-TRACTION-INVERTER$v$,$v$part.input_voltage_v$v$,$v$额定输入电压$v$,true,$v$NUMBER$v$,$v$V$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,2),
    ($v$CCU-TRACTION-INVERTER$v$,$v$part.output_power_kw$v$,$v$额定输出功率$v$,true,$v$NUMBER$v$,$v$kW$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,3),
    ($v$CCU-TRACTION-INVERTER$v$,$v$part.output_current_type$v$,$v$输出电流形式$v$,true,$v$ENUM$v$,NULL,$j$"CONTROLLED_AC"$j$::jsonb,$j$["CONTROLLED_AC","DC","OTHER"]$j$::jsonb,$v$企业工程$v$,4),
    ($v$CCU-TRACTION-INVERTER$v$,$v$part.integrated_motor_controller$v$,$v$是否集成电机控制器$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,5),
    ($v$CCU-TRACTION-INVERTER$v$,$v$part.integrated_dc_dc$v$,$v$是否集成DC-DC$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,6),
    ($v$CCU-TRACTION-INVERTER$v$,$v$part.integrated_onboard_charger$v$,$v$是否集成OBC$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,7),
    ($v$CCU-TRACTION-INVERTER$v$,$v$shipment.assembly_state$v$,$v$进口呈验状态$v$,true,$v$ENUM$v$,NULL,$j$"COMPLETE"$j$::jsonb,$j$["COMPLETE","INCOMPLETE","UNASSEMBLED","DISASSEMBLED","PARTIAL_SET","UNKNOWN"]$j$::jsonb,$v$物流包装$v$,8),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$part.primary_function$v$,$v$主要功能$v$,true,$v$ENUM$v$,NULL,$j$"BATTERY_CHARGING"$j$::jsonb,$j$["BATTERY_CHARGING","AC_TO_DC_RECTIFICATION","MULTIFUNCTION","OTHER"]$j$::jsonb,$v$企业工程$v$,1),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$part.rating_kva$v$,$v$额定容量$v$,true,$v$NUMBER$v$,$v$kVA$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,2),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$part.rated_power_kw$v$,$v$额定功率$v$,true,$v$NUMBER$v$,$v$kW$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,3),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$part.ac_input_phase$v$,$v$交流输入相数$v$,true,$v$ENUM$v$,NULL,NULL,$j$["SINGLE_PHASE","THREE_PHASE","MULTI_MODE","UNKNOWN"]$j$::jsonb,$v$企业工程$v$,4),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$part.ac_input_voltage_v$v$,$v$交流输入电压范围$v$,true,$v$TEXT$v$,$v$V$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,5),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$part.bidirectional$v$,$v$是否双向V2G/V2L$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,6),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$part.integrated_dc_dc$v$,$v$是否集成DC-DC$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,7),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$part.wireless_wpt_function$v$,$v$是否具备无线充电/WPT$v$,true,$v$BOOLEAN$v$,NULL,$j$"否"$j$::jsonb,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,8),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$part.domestic_electrical_apparatus_scope$v$,$v$是否属于家用电器/适配器监管描述$v$,true,$v$ENUM$v$,NULL,$j$"待确认"$j$::jsonb,$j$["是","否","待确认"]$j$::jsonb,$v$法规认证$v$,9),
    ($v$CCU-ONBOARD-CHARGER$v$,$v$shipment.assembly_state$v$,$v$进口呈验状态$v$,true,$v$ENUM$v$,NULL,$j$"COMPLETE"$j$::jsonb,$j$["COMPLETE","INCOMPLETE","UNASSEMBLED","DISASSEMBLED","PARTIAL_SET","UNKNOWN"]$j$::jsonb,$v$物流包装$v$,10),
    ($v$CCU-DC-DC-CONVERTER$v$,$v$part.primary_function$v$,$v$主要功能$v$,true,$v$ENUM$v$,NULL,$j$"DC_TO_DC_CONVERSION"$j$::jsonb,$j$["DC_TO_DC_CONVERSION","BATTERY_CHARGING","INVERSION","MULTIFUNCTION"]$j$::jsonb,$v$企业工程$v$,1),
    ($v$CCU-DC-DC-CONVERTER$v$,$v$part.input_voltage_v$v$,$v$输入电压范围$v$,true,$v$TEXT$v$,$v$V$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,2),
    ($v$CCU-DC-DC-CONVERTER$v$,$v$part.output_voltage_v$v$,$v$输出电压范围$v$,true,$v$TEXT$v$,$v$V$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,3),
    ($v$CCU-DC-DC-CONVERTER$v$,$v$part.rated_power_kw$v$,$v$额定功率$v$,true,$v$NUMBER$v$,$v$kW$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,4),
    ($v$CCU-DC-DC-CONVERTER$v$,$v$part.bidirectional$v$,$v$是否双向$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,5),
    ($v$CCU-DC-DC-CONVERTER$v$,$v$part.integrated_charger$v$,$v$是否集成充电机$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,6),
    ($v$CCU-DC-DC-CONVERTER$v$,$v$part.integrated_inverter$v$,$v$是否集成逆变器$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,7),
    ($v$CCU-DC-DC-CONVERTER$v$,$v$part.integrated_obc$v$,$v$是否与OBC同壳体/同料号$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,8),
    ($v$CCU-DC-DC-CONVERTER$v$,$v$shipment.assembly_state$v$,$v$进口呈验状态$v$,true,$v$ENUM$v$,NULL,$j$"COMPLETE"$j$::jsonb,$j$["COMPLETE","INCOMPLETE","UNASSEMBLED","DISASSEMBLED","PARTIAL_SET","UNKNOWN"]$j$::jsonb,$v$物流包装$v$,9),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$vehicle.intended_heading$v$,$v$目标整车品目$v$,true,$v$ENUM$v$,NULL,$j$"8703"$j$::jsonb,$j$["8702","8703","8704","OTHER"]$j$::jsonb,$v$企业工程$v$,1),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$body.special_use$v$,$v$车身特殊用途$v$,true,$v$ENUM$v$,NULL,$j$"ORDINARY_PASSENGER_CAR"$j$::jsonb,$j$["ORDINARY_PASSENGER_CAR","GO_KART","GOLF_CAR","AMBULANCE","SNOW_VEHICLE","OTHER"]$j$::jsonb,$v$企业工程$v$,2),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$part.with_doors$v$,$v$是否带车门/闭合件$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,3),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$part.with_glass$v$,$v$是否带玻璃$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,4),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$part.with_interior_trim$v$,$v$是否带内饰$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,5),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$part.painted$v$,$v$是否涂装$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,6),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$shipment.assembly_state$v$,$v$车身进口呈验状态$v$,true,$v$ENUM$v$,NULL,$j$"INCOMPLETE"$j$::jsonb,$j$["COMPLETE","INCOMPLETE","UNASSEMBLED","DISASSEMBLED","PARTIAL_SET","UNKNOWN"]$j$::jsonb,$v$物流包装$v$,7),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$shipment.other_vehicle_components_presented$v$,$v$同批是否呈验其他主要车辆部件$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$物流包装$v$,8),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$shipment.rolling_chassis_presented$v$,$v$同批是否呈验底盘/车桥/悬架$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$物流包装$v$,9),
    ($v$CCU-PASSENGER-BODY-SHELL$v$,$v$shipment.powertrain_presented$v$,$v$同批是否呈验动力总成$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$物流包装$v$,10),
    ($v$CCU-ROAD-WHEEL$v$,$v$vehicle.intended_heading$v$,$v$目标整车品目$v$,true,$v$ENUM$v$,NULL,$j$"8703"$j$::jsonb,$j$["8701","8702","8703","8704","OTHER"]$j$::jsonb,$v$企业工程$v$,1),
    ($v$CCU-ROAD-WHEEL$v$,$v$part.component_form$v$,$v$部件形态$v$,true,$v$ENUM$v$,NULL,$j$"COMPLETE_WHEEL"$j$::jsonb,$j$["COMPLETE_WHEEL","HUB_CAP","OTHER_WHEEL_PART_OR_ACCESSORY"]$j$::jsonb,$v$企业工程$v$,2),
    ($v$CCU-ROAD-WHEEL$v$,$v$part.material$v$,$v$材料$v$,true,$v$ENUM$v$,NULL,NULL,$j$["STEEL","ALUMINIUM_ALLOY","MAGNESIUM_ALLOY","OTHER"]$j$::jsonb,$v$企业工程$v$,3),
    ($v$CCU-ROAD-WHEEL$v$,$v$part.diameter_inch$v$,$v$轮辋直径$v$,true,$v$NUMBER$v$,$v$inch$v$,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,4),
    ($v$CCU-ROAD-WHEEL$v$,$v$part.with_tyre$v$,$v$进口时是否装有轮胎$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,5),
    ($v$CCU-ROAD-WHEEL$v$,$v$part.with_hub$v$,$v$是否包含轮毂/轴承单元$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,6),
    ($v$CCU-ROAD-WHEEL$v$,$v$shipment.tyre_separately_invoiced$v$,$v$轮胎是否分开发票/申报$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$物流包装$v$,7),
    ($v$CCU-ROAD-WHEEL$v$,$v$shipment.assembly_state$v$,$v$进口呈验状态$v$,true,$v$ENUM$v$,NULL,$j$"COMPLETE"$j$::jsonb,$j$["COMPLETE","INCOMPLETE","UNASSEMBLED","DISASSEMBLED","PARTIAL_SET","UNKNOWN"]$j$::jsonb,$v$物流包装$v$,8),
    ($v$CCU-ROAD-WHEEL$v$,$v$part.intended_use$v$,$v$用途$v$,true,$v$ENUM$v$,NULL,$j$"OEM_KD"$j$::jsonb,$j$["OEM_KD","REPLACEMENT","SPARE_PART","OTHER"]$j$::jsonb,$v$企业工程$v$,9),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$vehicle.intended_heading$v$,$v$目标整车品目$v$,true,$v$ENUM$v$,NULL,$j$"8703"$j$::jsonb,$j$["8701","8702","8703","8704","OTHER"]$j$::jsonb,$v$企业工程$v$,1),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$part.component_type$v$,$v$具体部件类型$v$,true,$v$ENUM$v$,NULL,NULL,$j$["BRAKE_DRUM","BRAKE_DISC","BRAKE_PIPE","CALIPER","BRAKE_PAD","BRAKE_SHOE","FOUNDATION_BRAKE_ASSEMBLY","OTHER"]$j$::jsonb,$v$企业工程$v$,2),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$part.brake_type$v$,$v$制动形式$v$,true,$v$ENUM$v$,NULL,NULL,$j$["DISC","DRUM","MIXED","OTHER"]$j$::jsonb,$v$企业工程$v$,3),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$part.includes_caliper$v$,$v$是否包含卡钳$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,4),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$part.includes_disc_or_drum$v$,$v$是否包含制动盘/鼓$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,5),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$part.includes_pipe$v$,$v$是否包含制动管$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,6),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$part.includes_actuator$v$,$v$是否包含执行器$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,7),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$part.includes_pads_or_shoes$v$,$v$是否包含摩擦片/蹄$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,8),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$part.intended_use$v$,$v$用途$v$,true,$v$ENUM$v$,NULL,$j$"OEM_KD"$j$::jsonb,$j$["OEM_KD","REPLACEMENT","SPARE_PART","OTHER"]$j$::jsonb,$v$企业工程$v$,9),
    ($v$CCU-FOUNDATION-BRAKE$v$,$v$shipment.assembly_state$v$,$v$进口呈验状态$v$,true,$v$ENUM$v$,NULL,$j$"COMPLETE"$j$::jsonb,$j$["COMPLETE","INCOMPLETE","UNASSEMBLED","DISASSEMBLED","PARTIAL_SET","UNKNOWN"]$j$::jsonb,$v$物流包装$v$,10),
    ($v$CCU-STEERING-GEAR-COLUMN$v$,$v$vehicle.intended_heading$v$,$v$目标整车品目$v$,true,$v$ENUM$v$,NULL,$j$"8703"$j$::jsonb,$j$["8701","8702","8703","8704","OTHER"]$j$::jsonb,$v$企业工程$v$,1),
    ($v$CCU-STEERING-GEAR-COLUMN$v$,$v$part.component_type$v$,$v$具体部件类型$v$,true,$v$ENUM$v$,NULL,NULL,$j$["STEERING_GEAR","STEERING_RACK","STEERING_COLUMN","STEERING_WHEEL","OTHER"]$j$::jsonb,$v$企业工程$v$,2),
    ($v$CCU-STEERING-GEAR-COLUMN$v$,$v$part.assist_type$v$,$v$助力形式$v$,true,$v$ENUM$v$,NULL,NULL,$j$["MECHANICAL","HYDRAULIC","ELECTRO_HYDRAULIC","ELECTRIC","OTHER"]$j$::jsonb,$v$企业工程$v$,3),
    ($v$CCU-STEERING-GEAR-COLUMN$v$,$v$part.includes_electric_motor$v$,$v$是否集成电机$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,4),
    ($v$CCU-STEERING-GEAR-COLUMN$v$,$v$part.includes_ecu$v$,$v$是否集成ECU$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,5),
    ($v$CCU-STEERING-GEAR-COLUMN$v$,$v$part.steering_wheel_with_airbag$v$,$v$是否为带安全气囊方向盘$v$,true,$v$BOOLEAN$v$,NULL,$j$"否"$j$::jsonb,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,6),
    ($v$CCU-STEERING-GEAR-COLUMN$v$,$v$part.integrated_functions$v$,$v$其他集成功能$v$,false,$v$TEXT$v$,NULL,NULL,$j$[]$j$::jsonb,$v$企业工程$v$,7),
    ($v$CCU-STEERING-GEAR-COLUMN$v$,$v$shipment.assembly_state$v$,$v$进口呈验状态$v$,true,$v$ENUM$v$,NULL,$j$"COMPLETE"$j$::jsonb,$j$["COMPLETE","INCOMPLETE","UNASSEMBLED","DISASSEMBLED","PARTIAL_SET","UNKNOWN"]$j$::jsonb,$v$物流包装$v$,8),
    ($v$CCU-STEERING-GEAR-COLUMN$v$,$v$part.intended_use$v$,$v$用途$v$,true,$v$ENUM$v$,NULL,$j$"OEM_KD"$j$::jsonb,$j$["OEM_KD","REPLACEMENT","SPARE_PART","OTHER"]$j$::jsonb,$v$企业工程$v$,9),
    ($v$CCU-SHOCK-ABSORBER-STRUT$v$,$v$vehicle.intended_heading$v$,$v$目标整车品目$v$,true,$v$ENUM$v$,NULL,$j$"8703"$j$::jsonb,$j$["8701","8702","8703","8704","8705","OTHER"]$j$::jsonb,$v$企业工程$v$,1),
    ($v$CCU-SHOCK-ABSORBER-STRUT$v$,$v$part.presentation_scope$v$,$v$呈验对象范围$v$,true,$v$ENUM$v$,NULL,NULL,$j$["SHOCK_ABSORBER","STRUT","SUSPENSION_PART","COMPLETE_SUSPENSION_SYSTEM","OTHER"]$j$::jsonb,$v$企业工程$v$,2),
    ($v$CCU-SHOCK-ABSORBER-STRUT$v$,$v$part.configuration$v$,$v$结构形式$v$,true,$v$ENUM$v$,NULL,NULL,$j$["TWIN_TUBE","MONOTUBE","MACPHERSON_STRUT","AIR_DAMPER","OTHER"]$j$::jsonb,$v$企业工程$v$,3),
    ($v$CCU-SHOCK-ABSORBER-STRUT$v$,$v$part.electronic_controlled$v$,$v$是否电子可调$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,4),
    ($v$CCU-SHOCK-ABSORBER-STRUT$v$,$v$part.includes_spring$v$,$v$是否包含弹簧$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,5),
    ($v$CCU-SHOCK-ABSORBER-STRUT$v$,$v$part.includes_knuckle$v$,$v$是否包含转向节$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,6),
    ($v$CCU-SHOCK-ABSORBER-STRUT$v$,$v$part.includes_control_ecu$v$,$v$是否包含控制ECU$v$,true,$v$BOOLEAN$v$,NULL,NULL,$j$["是","否","待确认"]$j$::jsonb,$v$企业工程$v$,7),
    ($v$CCU-SHOCK-ABSORBER-STRUT$v$,$v$shipment.assembly_state$v$,$v$进口呈验状态$v$,true,$v$ENUM$v$,NULL,$j$"COMPLETE"$j$::jsonb,$j$["COMPLETE","INCOMPLETE","UNASSEMBLED","DISASSEMBLED","PARTIAL_SET","UNKNOWN"]$j$::jsonb,$v$物流包装$v$,8),
    ($v$CCU-SHOCK-ABSORBER-STRUT$v$,$v$part.intended_use$v$,$v$用途$v$,true,$v$ENUM$v$,NULL,$j$"OEM_KD"$j$::jsonb,$j$["OEM_KD","REPLACEMENT","SPARE_PART","OTHER"]$j$::jsonb,$v$企业工程$v$,9)
),
prepared AS (
  SELECT
    ccu.ccu_id,
    row.field_path,
    row.field_name_cn,
    row.required_at_use,
    row.value_type::ref.input_data_type AS value_type,
    row.unit,
    row.suggested_value,
    row.allowed_values,
    row.data_owner,
    row.display_order
  FROM requirement_rows row
  JOIN customs.customs_classification_unit ccu
    ON ccu.ccu_code = row.ccu_code
   AND ccu.version = 1
)
INSERT INTO customs.ccu_input_requirement (
  ccu_id,
  field_path,
  field_name_cn,
  field_name_en,
  required_at_use,
  value_type,
  unit,
  suggested_value,
  allowed_values,
  data_owner,
  guidance_cn,
  classification_impact_cn,
  evidence_required,
  display_order,
  effective_from,
  effective_to,
  version,
  record_status,
  verification_status
)
SELECT
  prepared.ccu_id,
  prepared.field_path,
  prepared.field_name_cn,
  NULL,
  prepared.required_at_use,
  prepared.value_type,
  prepared.unit,
  prepared.suggested_value,
  prepared.allowed_values,
  prepared.data_owner,
  '按企业技术参数采集模板填写，并关联规格书、图纸、BOM或装箱文件。',
  '字段在最终马来西亚税号选择、GRI 2(a)、8708排除或进口监管判断时使用。',
  true,
  prepared.display_order,
  DATE '2025-11-01',
  NULL,
  1,
  'ACTIVE',
  'VERIFIED'
FROM prepared
ON CONFLICT (ccu_id, field_path, version) DO UPDATE
SET
  field_name_cn = EXCLUDED.field_name_cn,
  required_at_use = EXCLUDED.required_at_use,
  value_type = EXCLUDED.value_type,
  unit = EXCLUDED.unit,
  suggested_value = EXCLUDED.suggested_value,
  allowed_values = EXCLUDED.allowed_values,
  data_owner = EXCLUDED.data_owner,
  guidance_cn = EXCLUDED.guidance_cn,
  classification_impact_cn = EXCLUDED.classification_impact_cn,
  evidence_required = EXCLUDED.evidence_required,
  display_order = EXCLUDED.display_order,
  effective_from = EXCLUDED.effective_from,
  effective_to = EXCLUDED.effective_to,
  record_status = EXCLUDED.record_status,
  verification_status = EXCLUDED.verification_status,
  updated_at = now();

WITH required_fields AS (
  SELECT
    requirement.ccu_id,
    jsonb_agg(
      to_jsonb(requirement.field_path)
      ORDER BY requirement.display_order
    ) FILTER (WHERE requirement.required_at_use) AS field_paths
  FROM customs.ccu_input_requirement requirement
  WHERE requirement.record_status = 'ACTIVE'
    AND requirement.version = 1
  GROUP BY requirement.ccu_id
)
UPDATE customs.customs_classification_unit ccu
SET
  required_input_fields = required_fields.field_paths,
  updated_at = now()
FROM required_fields
WHERE required_fields.ccu_id = ccu.ccu_id;

DO $$
DECLARE
  link_record record;
BEGIN
  FOR link_record IN
    SELECT part_ccu_link_id
    FROM enterprise.enterprise_part_ccu_link
  LOOP
    PERFORM enterprise.sync_part_ccu_input_slots(
      link_record.part_ccu_link_id
    );
  END LOOP;
END
$$;

UPDATE audit.missing_data
SET
  description =
    'Enterprise technical facts are intentionally deferred. Empty database slots are retained and the required fields must be supplied before an input snapshot, final classification or calculation can proceed.',
  blocking_scope =
    'USAGE_TIME_CLASSIFICATION_AND_CALCULATION',
  priority = 'P0',
  next_action =
    'When a real enterprise part is linked to this CCU, fill the generated enterprise.part_ccu_input_value rows and set each required value to PROVIDED or VERIFIED.',
  status = 'WAITING_ENTERPRISE',
  resolved_at = NULL
WHERE field_path LIKE 'enterprise.classification_input[CCU-%]%';

COMMIT;
