/** Display and matching helpers for Vietnam's national tariff descriptions.
 *
 * The source data is the Vietnamese tariff wording.  We deliberately keep
 * that wording visible as a secondary reference, while showing a stable
 * Chinese translation first.  This is a UI translation layer, not a legal
 * reclassification engine: unknown wording is never silently guessed.
 */

export type VietnamTariffCandidate = {
  agreement: string;
  national_tariff_code: string;
  tariff_description: string;
  import_duty_rate: string | null;
  verification_status: string;
};

const PHRASE_TRANSLATIONS: Array<[RegExp, string]> = [
  [/Dung tích xi lanh không quá\s*([\d.]+)\s*cc/i, "气缸排量不超过 $1 cc"],
  [/Dung tích xi lanh trên\s*([\d.]+)\s*cc nhưng không quá\s*([\d.]+)\s*cc/i, "气缸排量超过 $1 cc但不超过 $2 cc"],
  [/Dung tích xi lanh trên\s*([\d.]+)\s*cc/i, "气缸排量超过 $1 cc"],
  [/Dùng cho xe đua cỡ nhỏ và xe chơi gôn \(kể cả xe golf buggies\) và các loại xe tương tự/i, "用于小型赛车、高尔夫球车（包括高尔夫球车）及类似车辆"],
  [/Dùng cho xe thuộc phân nhóm\s*8704\.10/i, "用于8704.10子目车辆"],
  [/Dùng cho xe có động cơ khác/i, "用于其他机动车"],
  [/^Thùng nhiên liệu$/i, "燃油箱"],
  [/^Các bộ phận khác$/i, "其他部件"],
  [/^Khung giá đỡ động cơ$/i, "发动机支架"],
  [/^Chân ga \(bàn đạp ga\), chân phanh \(bàn đạp phanh\) hoặc chân côn \(bàn đạp côn\)$/i, "油门、制动或离合器踏板"],
  [/^Giá đỡ hoặc khay đỡ bình ắc quy và khung của nó$/i, "蓄电池支架或托盘及其框架"],
  [/Loại sử dụng cho ô tô con \(motor car\) \(kể cả loại ô tô chở người có khoang chở hành lý chung \(station wagons\) và ô tô đua\)/i, "用于乘用车（包括旅行车和赛车）"],
  [/Phù hợp dùng cho phương tiện bay hoặc tàu vũ trụ thuộc Chương\s*88/i, "适用于第88章航空器或航天器"],
  [/Bảng chỉ báo có gắn màn hình tinh thể lỏng \(LCD\) hoặc đi-ốt phát quang \(LED\)/i, "带LCD或LED显示屏的指示面板"],
  [/Với đường kính cửa hút không quá\s*200\s*mm/i, "吸入口直径不超过200毫米"],
  [/Với đường kính cửa hút trên\s*200\s*mm/i, "吸入口直径超过200毫米"],
  [/Bơm nước, với lưu lượng trên\s*8\.000\s*m³\/h nhưng không quá\s*13\.000\s*m³\/h/i, "流量超过8,000立方米/小时但不超过13,000立方米/小时的水泵"],
  [/Loại dùng cho máy tính xách tay.*notebook và subnotebook/i, "适用于笔记本电脑（包括notebook和subnotebook）"],
  [/Dùng cho máy bay/i, "用于飞机"],
  [/Dùng cho xe thuộc Chương\s*87/i, "用于第87章车辆"],
  [/Loại dùng cho hàng hóa thuộc nhóm\s*([\d.、\s]+)\.?/i, "适用于$1组商品"],
  [/Loại dùng cho xe của Chương\s*87/i, "用于第87章车辆"],
  [/Bộ nguồn cấp điện liên tục \(UPS\)/i, "不间断电源（UPS）"],
  [/Máy nạp ắc qui, pin có công suất danh định trên\s*100\s*kVA/i, "额定功率超过100 kVA的蓄电池/电池充电器"],
  [/Bộ chỉnh lưu khác/i, "其他整流器"],
  [/Bộ nghịch lưu/i, "逆变器"],
  [/Bảng điều khiển của loại thích hợp sử dụng cho hệ thống điều khiển phân tán/i, "适用于分布式控制系统的控制面板"],
  [/Bảng điều khiển có trang bị bộ xử lý lập trình/i, "配有可编程处理器的控制面板"],
  [/Bảng điều khiển khác của loại thích hợp dùng cho hàng hóa của nhóm.*$/i, "适用于指定商品组的其他控制面板"],
  [/Bảng phân phối .*chỉ dùng hoặc chủ yếu dùng với các hàng hóa thuộc nhóm.*$/i, "仅用于或主要用于指定商品组的配电板"],
  [/Bộ điều khiển logic có khả năng lập trình.*thiết bị bán dẫn/i, "用于半导体设备的可编程逻辑控制器"],
  [/Bộ điều khiển động cơ có điện áp đầu ra từ\s*24V đến\s*120VDC.*300A đến\s*500A/i, "输出电压24V至120VDC、电流300A至500A的电机控制器"],
  [/Loại sử dụng trong các thiết bị sóng vô tuyến hoặc quạt điện/i, "用于无线电波设备或电风扇"],
  [/Loại phù hợp sử dụng cho hệ thống điều khiển phân tán/i, "适用于分布式控制系统"],
  [/Dùng cho xe thuộc nhóm\s*87\.03/i, "用于87.03组乘用车"],
  [/Dùng cho xe có động cơ thuộc nhóm\s*87\.02,\s*87\.03\s*hoặc\s*87\.04/i, "用于87.02、87.03或87.04组机动车"],
  [/Dùng cho ô tô con \(motor car\).*station wagons.*ô tô đua/i, "用于乘用车（含旅行车和赛车）"],
  [/Phù hợp dùng cho xe thuộc Chương\s*87/i, "适用于第87章车辆"],
  [/Dùng cho xe đua cỡ nhỏ.*xe chơi gôn.*xe golf buggies/i, "用于小型赛车、高尔夫球车及类似车辆"],
  [/Dùng cho ô tô cứu thương/i, "用于救护车"],
  [/Dùng cho xe được thiết kế đặc biệt để đi trên tuyết/i, "用于专为雪地行驶设计的车辆"],
  [/Dùng cho xe tự đổ được thiết kế.*trên 45 tấn/i, "用于非公路自卸车（设计总质量超过45吨）"],
  [/Cách điện bằng cao su hoặc plastic/i, "橡胶或塑料绝缘"],
  [/Thiết bị chiếu sáng hoặc tạo tín hiệu trực quan chưa lắp ráp/i, "未组装的照明或视觉信号装置"],
  [/Bảng chỉ báo có gắn màn hình tinh thể lỏng.*LED/i, "带LCD或LED显示屏的指示面板"],
  [/Đồng hồ tốc độ dùng cho xe có động cơ/i, "机动车用车速表"],
  [/Máy đo tốc độ góc cho xe có động cơ/i, "机动车用转速表"],
  [/Dây đai an toàn/i, "安全带"],
  [/Lót và đệm phanh/i, "制动衬片和制动垫"],
  [/Bơm nhiên liệu loại sử dụng cho động cơ.*87\.02,\s*87\.03\s*hoặc\s*87\.04/i, "用于87.02、87.03或87.04组机动车发动机的燃油泵"],
  [/Bơm nước loại được sử dụng cho động cơ.*87\.02,\s*87\.03\s*hoặc\s*87\.04/i, "用于87.02、87.03或87.04组机动车发动机的水泵"],
  [/Bơm nước.*hoạt động bằng điện/i, "电动水泵"],
  [/Bơm nước.*không hoạt động bằng điện/i, "非电动水泵"],
  [/Thùng nhiên liệu chưa lắp ráp; khung giá đỡ động cơ/i, "未组装燃油箱；发动机支架"],
  [/Nửa dưới của thùng nhiên liệu.*đai giữ bình nhiên liệu/i, "燃油箱下半部、燃油箱盖、管路、加油软管及燃油箱固定带"],
  [/Chân ga.*chân phanh.*chân côn/i, "油门、制动或离合器踏板"],
  [/Giá đỡ hoặc khay đỡ bình ắc quy/i, "蓄电池支架或托盘及其框架"],
  [/Tấm hướng luồng khí tản nhiệt/i, "散热气流导流板"],
  [/Bánh răng vành khăn và bánh răng quả dứa/i, "齿圈和小齿轮"],
  [/Loại khác/i, "其他"],
  [/Của xe thuộc nhóm\s*87\.02,\s*87\.03\s*hoặc\s*87\.04/i, "用于87.02、87.03或87.04组车辆"],
  [/Của xe thuộc nhóm\s*87\.03/i, "用于87.03组乘用车"],
  [/Phương tiện bay hoặc tàu vũ trụ thuộc Chương\s*88/i, "第88章航空器或航天器"],
  [/Loại sử dụng cho ô tô con/i, "用于乘用车"],
];

function cleanDescription(value: string | null | undefined) {
  return String(value ?? "").replace(/^[\s-]+/, "").trim();
}

export function translateVietnameseTariffDescription(value: string | null | undefined): string {
  const raw = cleanDescription(value);
  if (!raw) return "中文说明待补充";
  for (const [pattern, translation] of PHRASE_TRANSLATIONS) {
    if (pattern.test(raw)) {
      return raw.replace(pattern, translation).replace(/\s+/g, " ").trim();
    }
  }
  return "中文说明待补充";
}

export function formatVietnameseCandidate(candidate: VietnamTariffCandidate): string {
  const chinese = translateVietnameseTariffDescription(candidate.tariff_description);
  const raw = cleanDescription(candidate.tariff_description);
  return `${candidate.national_tariff_code} · ${candidate.agreement} · ${chinese} · 越南原文：${raw}`;
}

export function factLabel(field: string): string {
  const labels: Record<string, string> = {
    "engine.displacement_cc": "发动机排量",
    "engine.spark_ignition": "点火方式（火花点火）",
    "engine.complete_engine": "完整发动机/发动机零件状态",
    "origin.country_iso2": "零件原产国",
    "part.transmission_or_reducer": "变速箱/减速器结构",
    "part.integrated_motor": "是否与电机一体化",
    "part.body_shell_or_panel": "车身外壳/车身面板状态",
    "vehicle.intended_heading": "整车用途（乘用车）",
    "part.frame_or_chassis_part": "底盘/车架部件状态",
    "part.with_engine_or_motor": "是否带发动机或电机",
    "part.axle_suspension_or_spring": "车桥/悬架/弹簧类型",
    "part.steering_wheel_column_box_or_part": "方向盘/转向柱/转向箱部件",
    "part.brake_system_or_friction_material": "制动系统/摩擦材料",
    "part.tyre_or_wheel": "轮胎或车轮类型",
    "part.size": "尺寸规格",
    "part.hvac_pump_or_cooling_module": "空调泵/冷却模块",
    "part.engine_mounted": "是否发动机安装件",
    "part.vehicle_wiring_set": "车辆线束",
    "part.voltage_level": "电压等级",
    "part.motor_vehicle_seat": "机动车座椅",
    "part.with_airbag_or_motor": "是否带气囊或电机",
    "part.tempered_or_laminated": "钢化/夹层玻璃",
    "part.vehicle_use": "车辆用途",
    "part.lighting_or_visual_signalling": "照明/视觉信号装置",
    "part.speedometer_display_or_panel": "车速表/显示面板",
    "part.airbag_or_safety_belt": "安全气囊/安全带",
  };
  return labels[field] ?? field;
}

function numericDisplacement(value: string | number | null | undefined): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function candidateBand(candidate: VietnamTariffCandidate): "UP_TO_2000" | "2000_TO_3000" | "ABOVE_3000" | null {
  const description = cleanDescription(candidate.tariff_description).toLowerCase();
  if (/không quá\s*2\.000\s*cc/.test(description)) return "UP_TO_2000";
  if (/trên\s*2\.000\s*cc.*không quá\s*3\.000\s*cc/.test(description)) return "2000_TO_3000";
  if (/trên\s*3\.000\s*cc/.test(description)) return "ABOVE_3000";
  return null;
}

export function candidateMatchesDisplacement(candidate: VietnamTariffCandidate, displacement: string | number | null | undefined): boolean {
  const cc = numericDisplacement(displacement);
  const band = candidateBand(candidate);
  if (cc == null || band == null) return false;
  if (band === "UP_TO_2000") return cc <= 2000;
  if (band === "2000_TO_3000") return cc > 2000 && cc <= 3000;
  return cc > 3000;
}

export function uniqueCandidateCodes(candidates: VietnamTariffCandidate[]): string[] {
  return [...new Set(candidates.map((candidate) => candidate.national_tariff_code))];
}

export function autoSelectCandidateCode(
  ccuCode: string,
  candidates: VietnamTariffCandidate[],
  displacement: string | number | null | undefined,
  engineAssembly: "COMPLETE" | "PARTS" | "UNKNOWN" = "UNKNOWN",
): { code: string | null; reason: string | null } {
  if (candidates.length === 0) return { code: null, reason: null };
  let narrowed = candidates;
  if (ccuCode.includes("ENGINE")) {
    const byDisplacement = candidates.filter((candidate) => candidateMatchesDisplacement(candidate, displacement));
    if (byDisplacement.length === 0) return { code: null, reason: "先填写发动机排量" };
    narrowed = byDisplacement;

    // The Vietnamese CKD schedules distinguish the fully assembled engine
    // branch from the "other"/non-complete branch.  The distinction is not
    // present in the short Vietnamese cell text, so use the national-code
    // branch only after the user has supplied that fact explicitly/defaulted
    // the form to a complete engine.
    if (engineAssembly !== "UNKNOWN") {
      const completePattern = ccuCode.includes("GASOLINE") ? /^8407347/ : /^8408202/;
      const partsPattern = ccuCode.includes("GASOLINE") ? /^8407349/ : /^8408209/;
      const assemblyPattern = engineAssembly === "COMPLETE" ? completePattern : partsPattern;
      const byAssembly = narrowed.filter((candidate) => assemblyPattern.test(candidate.national_tariff_code));
      if (byAssembly.length > 0) narrowed = byAssembly;
    }
  }
  const codes = uniqueCandidateCodes(narrowed);
  if (codes.length === 1) return { code: codes[0], reason: "根据已填写条件唯一匹配" };

  // Passenger-car context can disambiguate lines explicitly limited to 87.03.
  const passengerOnly = narrowed.filter((candidate) => /87\.03/.test(candidate.tariff_description));
  const passengerCodes = uniqueCandidateCodes(passengerOnly);
  if (passengerCodes.length === 1) return { code: passengerCodes[0], reason: "根据乘用车用途唯一匹配" };
  return { code: null, reason: codes.length > 1 ? "仍有多个合法候选，需确认零件技术状态" : null };
}
