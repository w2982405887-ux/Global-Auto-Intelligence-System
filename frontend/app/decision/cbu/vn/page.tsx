"use client";

import { ArrowLeft, BarChart3, CalendarDays, CarFront, ChevronDown, CircleAlert, Database, LoaderCircle, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  type QuickEstimatePath,
  type QuickEstimateResult,
  type VehicleTariffOption,
  createQuickEstimate,
  getVehicleTariffOptions,
} from "../../../lib/api";
import { PolicyReviewDrawer, PolicyReviewTrigger, quickPolicyToReview } from "../../../components/PolicyReviewDrawer";
import type { ScenarioWorkspaceProps } from "../../ScenarioWorkspace";

const POWERTRAINS = ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"];
const ORIGINS = [
  { code: "CN", label: "中国 · CN" },
  { code: "TH", label: "泰国 · TH" },
  { code: "ID", label: "印度尼西亚 · ID" },
  { code: "VN", label: "越南 · VN" },
  { code: "JP", label: "日本 · JP" },
  { code: "KR", label: "韩国 · KR" },
  { code: "ZZ", label: "其他/待确认" },
];
const BODY_FILTERS = [
  { value: "ALL", label: "不限定车身/用途" },
  { value: "SEDAN", label: "Sedan / 轿车" },
  { value: "OTHER_PASSENGER", label: "Other passenger car / 其他乘用车" },
  { value: "OTHER_MOTOR_CAR", label: "Other motor car / 其他机动车" },
  { value: "SPECIAL", label: "特殊用途车，如救护/灵车/囚车/ATV" },
];
const DISPLACEMENT_FILTERS = [
  { value: "ALL", label: "不限定排量" },
  { value: "LE_1000", label: "≤1,000cc" },
  { value: "GT_1000_LE_1500", label: "＞1,000–1,500cc" },
  { value: "GT_1500_LE_1800", label: "＞1,500–1,800cc" },
  { value: "GT_1800_LE_2000", label: "＞1,800–2,000cc" },
  { value: "GT_2000_LE_2500", label: "＞2,000–2,500cc" },
  { value: "GT_2500_LE_3000", label: "＞2,500–3,000cc" },
  { value: "GT_3000", label: "＞3,000cc" },
];
function rateText(value: string | null | undefined) {
  if (value == null || value === "") return "待确认";
  const n = Number(value);
  if (Number.isNaN(n)) return "待确认";
  return `${(n * 100).toFixed(2).replace(/\.00$/, "")}%`;
}

function confidenceText(value: string | null | undefined) {
  return value === "HIGH" ? "高" : value === "MEDIUM" ? "中" : "低";
}

function normalizeDescription(value: string) {
  return value.toLowerCase().replace(/,/g, "").replace(/≤/g, "<=").replace(/＞/g, ">").replace(/–/g, "-");
}

function bodyKind(item: VehicleTariffOption) {
  const text = normalizeDescription(item.tariff_description);
  if (text.includes("sedan")) return "SEDAN";
  if (text.includes("ambulance") || text.includes("hearse") || text.includes("prison") || text.includes("atv") || text.includes("motor-home") || text.includes("motorhome")) return "SPECIAL";
  if (text.includes("other passenger car")) return "OTHER_PASSENGER";
  if (text.includes("other motor car")) return "OTHER_MOTOR_CAR";
  return "ALL";
}

function displacementKind(item: VehicleTariffOption) {
  const text = normalizeDescription(item.tariff_description);
  if (text.includes("<=1000cc") || text.includes("not over 1000 cc") || text.includes("không quá 1.000")) return "LE_1000";
  if (text.includes(">1000-1500cc") || text.includes("over 1000") && text.includes("1500")) return "GT_1000_LE_1500";
  if (text.includes(">1500-1800cc") || text.includes("over 1500") && text.includes("1800")) return "GT_1500_LE_1800";
  if (text.includes(">1800-2000cc") || text.includes("over 1800") && text.includes("2000")) return "GT_1800_LE_2000";
  if (text.includes(">2000-2500cc") || text.includes("over 2000") && text.includes("2500")) return "GT_2000_LE_2500";
  if (text.includes(">2500-3000cc") || text.includes("over 2500") && text.includes("3000")) return "GT_2500_LE_3000";
  if (text.includes(">3000cc") || text.includes("over 3000") || text.includes("trên 3.000")) return "GT_3000";
  return "ALL";
}

function driveKind(item: VehicleTariffOption) {
  const text = normalizeDescription(item.tariff_description);
  if (text.includes("non-4wd") || text.includes("không phải loại bốn bánh")) return "NON_4WD";
  if (text.includes("4wd") || text.includes("bốn bánh chủ động")) return "4WD";
  return "ALL";
}

function VnCbuResultCard({ item }: { item: QuickEstimatePath }) {
  const [open, setOpen] = useState(true);
  return (
    <article className="quick-path-card">
      <header>
        <div className="quick-path-icon cbu"><CarFront size={22} /></div>
        <div><span>越南整车进口</span><h3>CBU</h3></div>
        <span className={`confidence ${item.confidence.toLowerCase()}`}>可信度 {confidenceText(item.confidence)}</span>
      </header>
      <div className="quick-rate-pair">
        <div><span>法定综合税率</span><strong>{rateText(item.statutory.effective_tax_rate)}</strong><small>{item.statutory.regime ?? "MFN"}</small></div>
        <div className="preferred"><span>优惠情景</span><strong>{rateText(item.incentive.effective_tax_rate)}</strong><small>{item.incentive.regime ?? "FTA/优惠资格待确认"}</small></div>
      </div>
      <dl className="quick-path-facts">
        <div><dt>匹配税号</dt><dd>{item.matched_tariff?.national_tariff_code ?? item.classification_scope?.final_national_tariff_code ?? "待确认"}</dd></div>
        <div><dt>推荐用途</dt><dd>{item.recommended_use}</dd></div>
        <div><dt>优惠依赖</dt><dd>{item.dependency_level === "HIGH" ? "高" : "低"}</dd></div>
      </dl>
      {item.missing_items.length > 0 && <div className="quick-missing"><CircleAlert size={15} /><span>仍需确认：{item.missing_items.join("、")}</span></div>}
      <button type="button" className="quick-detail-toggle" onClick={() => setOpen((current) => !current)}>查看税负拆分 <ChevronDown className={open ? "rotated" : ""} size={16} /></button>
      {open && <div className="quick-tax-lines">{item.statutory.tax_lines.map((line) => <div key={line.tax}><span>{line.tax}</span><span>{rateText(line.rate)}</span><strong>{line.amount == null ? "未计入" : `${line.amount} / 税基100`}</strong><small>{line.formula}</small></div>)}</div>}
    </article>
  );
}

export function VietnamCbuWorkspace({ embedded = false, onSnapshot }: ScenarioWorkspaceProps) {
  const [form, setForm] = useState({
    effective_date: new Date().toISOString().slice(0, 10),
    origin_country_iso2: "CN",
    powertrain: "BEV",
    cbu_tariff_code: "",
    body_filter: "ALL",
    displacement_filter: "ALL",
  });
  const needsDisplacement = !["BEV", "FCEV"].includes(form.powertrain);
  const [tariffs, setTariffs] = useState<VehicleTariffOption[]>([]);
  const [tariffsBusy, setTariffsBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QuickEstimateResult | null>(null);
  const [selectedPolicy, setSelectedPolicy] = useState<NonNullable<QuickEstimateResult["policy_matches"]>[number] | null>(null);

  useEffect(() => {
    onSnapshot?.(null);
  }, [form.effective_date, form.origin_country_iso2, form.powertrain, form.cbu_tariff_code, form.body_filter, form.displacement_filter, onSnapshot]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setTariffsBusy(true);
      setError(null);
      setResult(null);
      setForm((current) => ({ ...current, cbu_tariff_code: "" }));
      try {
        const data = await getVehicleTariffOptions("VN", "ROUTE-VN-01-CBU-NEW-PASSENGER", form.powertrain, form.effective_date);
        if (!cancelled) setTariffs(data.items);
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "读取越南CBU税号候选失败");
      } finally {
        if (!cancelled) setTariffsBusy(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [form.effective_date, form.powertrain]);

  async function calculate() {
    setBusy(true);
    setError(null);
    try {
      const data = await createQuickEstimate({
        country_iso2: "VN",
        origin_country_iso2: form.origin_country_iso2,
        effective_date: form.effective_date,
        path: "CBU",
        powertrain: form.powertrain,
        cbu_tariff_code: form.cbu_tariff_code,
        ckd_declaration_mode: "PARTS_BOM",
        ckd_tariff_code: null,
        customs_value_cbu: null,
        customs_value_ckd: null,
      });
      setResult(data);
      const path = data.paths.find((item) => item.path === "CBU");
      if (path) {
        const rates = [
          {
            regime: path.statutory.regime ?? "MFN",
            rate: path.statutory.effective_tax_rate,
            scope: "FULL_CHAIN" as const,
            complete: path.statutory.is_complete_statutory_chain,
          },
          {
            regime: path.incentive.regime ?? "优惠候选",
            rate: path.incentive.effective_tax_rate,
            scope: "FULL_CHAIN" as const,
            complete: path.incentive.is_complete_statutory_chain,
          },
        ].filter((item, index, items) => items.findIndex((candidate) => candidate.regime === item.regime && candidate.rate === item.rate) === index);
        onSnapshot?.({
          countryIso2: "VN",
          countryName: "越南",
          route: "CBU",
          title: "越南 CBU 整车进口",
          effectiveDate: form.effective_date,
          originCountryIso2: form.origin_country_iso2,
          powertrain: form.powertrain,
          status: rates.some((item) => item.complete) ? "COMPLETE" : rates.some((item) => item.rate != null) ? "PARTIAL" : "BLOCKED",
          confidence: path.confidence,
          scopeLabel: "进口关税 + SCT + 进口 VAT",
          tariffCodes: [path.matched_tariff?.national_tariff_code ?? path.classification_scope?.final_national_tariff_code ?? form.cbu_tariff_code].filter(Boolean),
          rates,
          missingItems: path.missing_items,
          notes: data.assumptions.map((item) => `${item.condition}：${item.treatment}`),
        });
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "越南CBU计算失败");
    } finally {
      setBusy(false);
    }
  }

  const filteredTariffs = useMemo(() => {
    return tariffs.filter((item) => {
      const bodyOk = form.body_filter === "ALL" || bodyKind(item) === form.body_filter;
      const dispOk = !needsDisplacement || form.displacement_filter === "ALL" || displacementKind(item) === form.displacement_filter;
      const drive = driveKind(item);
      // Four-wheel drive is fixed for this business scope.  Generic tariff
      // descriptions ("Sedan", etc.) remain valid because the schedule does
      // not split those rows by drive; only explicit non-4WD rows are removed.
      const driveOk = drive !== "NON_4WD";
      return bodyOk && dispOk && driveOk;
    });
  }, [tariffs, form.body_filter, form.displacement_filter, needsDisplacement]);

  useEffect(() => {
    if (filteredTariffs.length === 1 && form.cbu_tariff_code !== filteredTariffs[0].national_tariff_code) {
      setForm((current) => ({ ...current, cbu_tariff_code: filteredTariffs[0].national_tariff_code }));
    } else if (form.cbu_tariff_code && !filteredTariffs.some((item) => item.national_tariff_code === form.cbu_tariff_code)) {
      setForm((current) => ({ ...current, cbu_tariff_code: "" }));
    }
  }, [filteredTariffs, form.cbu_tariff_code]);

  const cbuPath = result?.paths.find((item) => item.path === "CBU");

  return (
    <main className={`quick-decision-page${embedded ? " scenario-workspace-embedded" : ""}`}>
      <div className="quick-shell">
        <Link className="quick-back" href="/decision/cbu"><ArrowLeft size={17} /> 返回CBU国家选择</Link>
        <header className="quick-hero">
          <div>
            <span className="quick-eyebrow"><Sparkles size={14} /> VIETNAM CBU</span>
            <h1>越南 CBU 整车进口税务分析</h1>
            <p>当前越南 CBU 逻辑：日期 + 原产国 + 动力类型 + 越南整车税号，计算进口关税、特别消费税 SCT、进口 VAT，并匹配 FTA 与新能源等特殊政策。</p>
          </div>
          <span className="quick-db-state"><Database size={17} /> 实时读取规则数据库</span>
        </header>

        <section className="quick-input-card">
          <div className="quick-input-grid four-columns">
            <label><span>目标国家</span><input value="越南 · VN" disabled /></label>
            <label><span>原产国</span><select value={form.origin_country_iso2} onChange={(event) => setForm({ ...form, origin_country_iso2: event.target.value })}>{ORIGINS.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select></label>
            <label><span>生效日期</span><div className="input-with-icon"><CalendarDays size={17} /><input type="date" value={form.effective_date} onChange={(event) => setForm({ ...form, effective_date: event.target.value })} /></div></label>
            <label><span>动力类型</span><select value={form.powertrain} onChange={(event) => { const nextPowertrain = event.target.value; const nextNeedsDisplacement = !["BEV", "FCEV"].includes(nextPowertrain); setForm({ ...form, powertrain: nextPowertrain, cbu_tariff_code: "", displacement_filter: nextNeedsDisplacement ? form.displacement_filter : "ALL" }); }}>{POWERTRAINS.map((item) => <option key={item} value={item}>{item}</option>)}</select><small>{needsDisplacement ? "燃油/混动类通常需要排量细分" : "纯电/氢燃料不需要排量"}</small></label>
          </div>
          <div className="quick-input-grid four-columns" style={{ marginTop: 18 }}>
            <label><span>车身/用途细分</span><select value={form.body_filter} onChange={(event) => setForm({ ...form, body_filter: event.target.value, cbu_tariff_code: "" })}>{BODY_FILTERS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            {needsDisplacement && <label><span>发动机排量</span><select value={form.displacement_filter} onChange={(event) => setForm({ ...form, displacement_filter: event.target.value, cbu_tariff_code: "" })}>{DISPLACEMENT_FILTERS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select><small>用于 ICE/HEV/PHEV/EREV 税号细分</small></label>}
             <label><span>筛选结果</span><input value={`${filteredTariffs.length} 个候选税号`} disabled /><small>{filteredTariffs.length === 1 ? "已自动锁定唯一税号" : needsDisplacement ? "继续缩小条件，尽量得到唯一税号" : "BEV/FCEV 已跳过排量条件；系统按四驱业务口径筛选"}</small></label>
          </div>
          <div className="quick-classification-inputs">
            <label>
              <span>越南 CBU 申报税号</span>
              <select value={form.cbu_tariff_code} onChange={(event) => setForm({ ...form, cbu_tariff_code: event.target.value })}>
                <option value="">{tariffsBusy ? "正在读取数据库…" : filteredTariffs.length === 0 ? "没有匹配税号，请放宽筛选条件" : "请选择越南CBU税号"}</option>
                {filteredTariffs.map((item) => <option key={item.vehicle_tariff_rate_line_id} value={item.national_tariff_code}>{item.national_tariff_code} · {item.tariff_description}</option>)}
              </select>
               <small>系统按乘用车、四驱业务口径只保留匹配税号；若只剩一个会自动选中。</small>
            </label>
          </div>
          {error && <div className="quick-error">{error}</div>}
          <button type="button" className="quick-calculate" disabled={busy || tariffsBusy || !form.cbu_tariff_code} onClick={calculate}>{busy ? <LoaderCircle className="spin" size={18} /> : <BarChart3 size={18} />}计算越南 CBU 综合税率</button>
        </section>

        {result && cbuPath && <section className="quick-results"><div className="quick-recommendation"><div className="recommendation-primary"><span>路径</span><strong>CBU</strong></div><div><span>结果可信度</span><strong>{confidenceText(cbuPath.confidence)}</strong></div><p>{result.recommendation.summary}</p></div><div className="quick-result-grid"><VnCbuResultCard item={cbuPath} /></div>{result.policy_matches && result.policy_matches.length > 0 && <section className="quick-assumptions"><header><div><span>INCENTIVE MATCHING</span><h2>特殊政策匹配</h2></div><strong>按路径、动力类型、原产国匹配</strong></header><div>{result.policy_matches.map((policy) => <article className="vn-policy-card" key={policy.program_code}><strong>{policy.program_name_cn}</strong><p><span>{policy.match_status}</span><em>{policy.effect_on_calculation}</em></p><PolicyReviewTrigger onClick={() => setSelectedPolicy(policy)} /></article>)}</div></section>}<p className="quick-disclaimer">{result.disclaimer}</p></section>}
        <PolicyReviewDrawer policy={selectedPolicy ? quickPolicyToReview(selectedPolicy) : null} onClose={() => setSelectedPolicy(null)} />
      </div>
    </main>
  );
}

export default function VietnamCbuPage() {
  return <VietnamCbuWorkspace />;
}
