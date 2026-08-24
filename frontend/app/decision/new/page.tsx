"use client";

import { ArrowLeft, BarChart3, CalendarDays, CarFront, ChevronDown, CircleAlert, Database, Factory, LoaderCircle, Scale, Sparkles } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { countries, getDecisionCapability } from "../../data/countries";
import {
  type QuickEstimatePath,
  type QuickEstimateResult,
  type VehicleTariffOption,
  createQuickEstimate,
  getVehicleTariffOptions,
} from "../../lib/api";
import { PolicyReviewDrawer, PolicyReviewTrigger, quickPolicyToReview } from "../../components/PolicyReviewDrawer";

const powertrains = ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"];
const pathOptions = [
  { value: "AUTO", label: "CBU vs CKD", icon: Scale },
  { value: "CBU", label: "CBU", icon: CarFront },
  { value: "CKD", label: "CKD", icon: Factory },
] as const;

function rateText(value: string | null | undefined) {
  if (value == null || value === "") return "待确认";
  const n = Number(value);
  if (Number.isNaN(n)) return "待确认";
  return `${(n * 100).toFixed(2).replace(/\.00$/, "")}%`;
}

function confidenceText(value: string | null | undefined) {
  return value === "HIGH" ? "高" : value === "MEDIUM" ? "中" : "低";
}

function PathResultCard({ item }: { item: QuickEstimatePath }) {
  const [open, setOpen] = useState(false);
  return (
    <article className="quick-path-card">
      <header>
        <div className={`quick-path-icon ${item.path.toLowerCase()}`}>
          {item.path === "CBU" ? <CarFront size={22} /> : <Factory size={22} />}
        </div>
        <div>
          <span>{item.path === "CBU" ? "整车进口" : "本地组装"}</span>
          <h3>{item.path}</h3>
        </div>
        <span className={`confidence ${item.confidence.toLowerCase()}`}>可信度 {confidenceText(item.confidence)}</span>
      </header>

      <div className="quick-rate-pair">
        <div>
          <span>法定已知综合税率</span>
          <strong>{rateText(item.statutory.effective_tax_rate)}</strong>
          <small>{item.statutory.regime ?? "MFN"} 基准场景</small>
        </div>
        <div className="preferred">
          <span>可选优惠情景</span>
          <strong>{rateText(item.incentive.effective_tax_rate)}</strong>
          <small>{item.incentive.regime ?? "资格待确认"}</small>
        </div>
      </div>

      <dl className="quick-path-facts">
        <div>
          <dt>匹配税号</dt>
          <dd>{item.classification_scope?.final_national_tariff_code ?? item.matched_tariff?.national_tariff_code ?? item.classification_scope?.candidate_scope ?? "最终税号待确认"}</dd>
        </div>
        <div>
          <dt>优惠依赖</dt>
          <dd>{item.dependency_level === "HIGH" ? "高" : "低"}</dd>
        </div>
        <div>
          <dt>推荐用途</dt>
          <dd>{item.recommended_use}</dd>
        </div>
      </dl>

      {item.missing_items.length > 0 && (
        <div className="quick-missing"><CircleAlert size={15} /><span>仍需确认：{item.missing_items.join("、")}</span></div>
      )}

      <button type="button" className="quick-detail-toggle" onClick={() => setOpen((current) => !current)}>
        查看税负拆分 <ChevronDown className={open ? "rotated" : ""} size={16} />
      </button>
      {open && (
        <div className="quick-tax-lines">
          {item.statutory.tax_lines.map((line) => (
            <div key={line.tax}>
              <span>{line.tax}</span>
              <span>{rateText(line.rate)}</span>
              <strong>{line.amount == null ? "未计入" : `${line.amount} / 税基100`}</strong>
              <small>{line.formula}</small>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

export default function QuickDecisionPage() {
  const searchParams = useSearchParams();
  const requestedCountry = (searchParams.get("country") ?? "").toUpperCase();
  // Only an omitted/invalid query uses the default.  A valid but not-yet-
  // supported country code is preserved so it can never silently become MY
  // or VN when a new country is added to the intelligence map first.
  const initialCountry = /^[A-Z]{2}$/.test(requestedCountry)
    ? requestedCountry
    : "MY";
  const initialPathParam = searchParams.get("path");
  const initialPath = initialPathParam === "CBU" || initialPathParam === "CKD" ? initialPathParam : "AUTO";

  const [form, setForm] = useState({
    country_iso2: initialCountry,
    origin_country_iso2: "CN",
    effective_date: new Date().toISOString().slice(0, 10),
    powertrain: "BEV",
    path: initialPath as "AUTO" | "CBU" | "CKD",
    cbu_tariff_code: "",
    ckd_declaration_mode: (initialCountry === "VN" ? "PARTS_BOM" : "WHOLE_KIT") as "WHOLE_KIT" | "PARTS_BOM",
    ckd_tariff_code: "",
  });
  const [busy, setBusy] = useState(false);
  const [tariffsBusy, setTariffsBusy] = useState(false);
  const [cbuTariffs, setCbuTariffs] = useState<VehicleTariffOption[]>([]);
  const [ckdTariffs, setCkdTariffs] = useState<VehicleTariffOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QuickEstimateResult | null>(null);
  const [selectedPolicy, setSelectedPolicy] = useState<NonNullable<QuickEstimateResult["policy_matches"]>[number] | null>(null);

  const selectedCountry = countries.find((country) => country.code === form.country_iso2);
  const countryCapability = getDecisionCapability(form.country_iso2);
  const countrySupportsEstimate = countryCapability.cbu || countryCapability.ckd;

  useEffect(() => {
    let cancelled = false;
    async function loadTariffs() {
      setTariffsBusy(true);
      setError(null);
      setResult(null);
      setForm((current) => ({ ...current, cbu_tariff_code: "", ckd_tariff_code: "" }));
      if (!countrySupportsEstimate) {
        setCbuTariffs([]);
        setCkdTariffs([]);
        setTariffsBusy(false);
        return;
      }
      try {
        const cbuRoute = form.country_iso2 === "VN" ? "ROUTE-VN-01-CBU-NEW-PASSENGER" : "ROUTE-MY-01-CBU";
        const ckdRoute = form.country_iso2 === "VN" ? "ROUTE-VN-CKD-PARTS-MAJOR-ESTIMATE" : "ROUTE-MY-02-CKD-WHOLE-KIT";
        const [cbu, ckd] = await Promise.all([
          getVehicleTariffOptions(form.country_iso2, cbuRoute, form.powertrain, form.effective_date),
          form.country_iso2 === "VN" ? Promise.resolve({ total: 0, items: [] }) : getVehicleTariffOptions(form.country_iso2, ckdRoute, form.powertrain, form.effective_date),
        ]);
        if (!cancelled) {
          setCbuTariffs(cbu.items);
          setCkdTariffs(ckd.items);
        }
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "读取税号候选失败");
      } finally {
        if (!cancelled) setTariffsBusy(false);
      }
    }
    loadTariffs();
    return () => { cancelled = true; };
  }, [countrySupportsEstimate, form.country_iso2, form.effective_date, form.powertrain]);

  const needsCbu = countryCapability.cbu && (form.path === "AUTO" || form.path === "CBU");
  const needsCkd = countryCapability.ckd && (form.path === "AUTO" || form.path === "CKD") && form.ckd_declaration_mode === "WHOLE_KIT";
  const canCalculate = countrySupportsEstimate && !tariffsBusy && (!needsCbu || Boolean(form.cbu_tariff_code)) && (!needsCkd || Boolean(form.ckd_tariff_code));

  async function calculate() {
    if (!countrySupportsEstimate) {
      setError(`${selectedCountry?.name ?? form.country_iso2}的 CBU/CKD 测算模块尚未接入，系统没有回退到其他国家。`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setResult(await createQuickEstimate({
        ...form,
        cbu_tariff_code: form.cbu_tariff_code || null,
        ckd_tariff_code: form.ckd_tariff_code || null,
        customs_value_cbu: null,
        customs_value_ckd: null,
      }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "快速测算失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="quick-decision-page">
      <div className="quick-shell">
        <Link className="quick-back" href="/"><ArrowLeft size={17} /> 返回全球决策</Link>
        <header className="quick-hero">
          <div>
            <span className="quick-eyebrow"><Sparkles size={14} /> POLICY QUICK ESTIMATE</span>
            <h1>{selectedCountry ? `${selectedCountry.name}汽车出口税负快速测算` : `${form.country_iso2}汽车出口税负快速测算`}</h1>
            <p>先选国家，再选路径。公开规则快速估算，不作为正式报关结论。</p>
          </div>
          <span className="quick-db-state"><Database size={17} /> 实时读取规则数据库</span>
        </header>

        <section className="quick-input-card">
          <div className="quick-input-grid four-columns">
            <label><span>目标国家</span><select value={form.country_iso2} onChange={(event) => setForm({ ...form, country_iso2: event.target.value, ckd_declaration_mode: event.target.value === "VN" ? "PARTS_BOM" : "WHOLE_KIT" })}>{countries.map((country) => { const capability = getDecisionCapability(country.code); const supported = capability.cbu || capability.ckd; return <option key={country.code} value={country.code} disabled={!supported}>{country.name} · {country.code}{supported ? "" : " · 模块建设中"}</option>; })}</select><small>{countrySupportsEstimate ? "国家模块已接入，可继续选择 CBU 或 CKD。" : "该国家已保留在情报库，但 CBU/CKD 计算模块尚未接入。"}</small></label>
            <label><span>原产国</span><select value={form.origin_country_iso2} onChange={(event) => setForm({ ...form, origin_country_iso2: event.target.value })}><option value="CN">中国 · CN</option><option value="TH">泰国 · TH</option><option value="ID">印度尼西亚 · ID</option><option value="VN">越南 · VN</option><option value="JP">日本 · JP</option><option value="KR">韩国 · KR</option><option value="ZZ">其他/待确认</option></select></label>
            <label><span>生效日期</span><div className="input-with-icon"><CalendarDays size={17} /><input type="date" value={form.effective_date} onChange={(event) => setForm({ ...form, effective_date: event.target.value })} /></div></label>
            <label><span>动力类型</span><select value={form.powertrain} onChange={(event) => setForm({ ...form, powertrain: event.target.value })}>{powertrains.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          </div>

          <div className="quick-path-picker"><span>比较路径</span><div>{pathOptions.map((option) => { const Icon = option.icon; return <button key={option.value} type="button" className={form.path === option.value ? "active" : ""} onClick={() => setForm({ ...form, path: option.value })}><Icon size={17} />{option.label}</button>; })}</div></div>

          {!countrySupportsEstimate && <div className="quick-country-notice"><CircleAlert size={17} /><span>当前国家的方案入口已正确保留，但数据库尚未提供可计算的 CBU/CKD 规则。请先完成该国模块后再计算。</span></div>}

          <div className="quick-classification-inputs">
            {needsCbu && <label><span>CBU申报税号</span><select value={form.cbu_tariff_code} onChange={(event) => setForm({ ...form, cbu_tariff_code: event.target.value })}><option value="">{tariffsBusy ? "正在读取数据库…" : "请选择CBU税号"}</option>{cbuTariffs.map((item) => <option key={item.vehicle_tariff_rate_line_id} value={item.national_tariff_code}>{item.national_tariff_code} · {item.tariff_description}</option>)}</select><small>候选来自有效期内的数据库记录，系统不会替你瞎选。</small></label>}
            {(form.path === "AUTO" || form.path === "CKD") && <div className="quick-ckd-classification"><label><span>CKD申报方式</span><select value={form.ckd_declaration_mode} onChange={(event) => setForm({ ...form, ckd_declaration_mode: event.target.value as "WHOLE_KIT" | "PARTS_BOM" })}>{form.country_iso2 !== "VN" && <option value="WHOLE_KIT">整套CKD单一税号</option>}<option value="PARTS_BOM">零部件BOM多税号/主要大件估算</option></select></label>{form.country_iso2 !== "VN" && form.ckd_declaration_mode === "WHOLE_KIT" ? <label><span>CKD申报税号</span><select value={form.ckd_tariff_code} onChange={(event) => setForm({ ...form, ckd_tariff_code: event.target.value })}><option value="">{tariffsBusy ? "正在读取数据库…" : "请选择CKD税号"}</option>{ckdTariffs.map((item) => <option key={item.vehicle_tariff_rate_line_id} value={item.national_tariff_code}>{item.national_tariff_code} · {item.tariff_description}</option>)}</select></label> : <div className="quick-bom-note">当前使用主要零件多税号估算；完整BOM和本地组装税费后续继续补齐。</div>}</div>}
          </div>

          {error && <div className="quick-error">{error}</div>}
          <button type="button" className="quick-calculate" disabled={busy || !canCalculate} onClick={calculate}>{busy ? <LoaderCircle className="spin" size={18} /> : <BarChart3 size={18} />}生成税负对比</button>
        </section>

        {result && <section className="quick-results"><div className="quick-recommendation"><div className="recommendation-primary"><span>推荐路径</span><strong>{result.recommendation.recommended_path ?? "暂不排名"}</strong></div><div><span>结果可信度</span><strong>{confidenceText(result.recommendation.confidence)}</strong></div><p>{result.recommendation.summary}</p></div><div className="quick-result-grid">{result.paths.map((item) => <PathResultCard key={item.path} item={item} />)}</div>{result.policy_matches && result.policy_matches.length > 0 && <section className="quick-assumptions"><header><div><span>INCENTIVE MATCHING</span><h2>特殊政策匹配</h2></div><strong>已按路径、动力类型、原产国匹配</strong></header><div>{result.policy_matches.map((policy) => <article key={policy.program_code}><strong>{policy.program_name_cn}</strong><p>{policy.match_status} · {policy.effect_on_calculation}</p><PolicyReviewTrigger onClick={() => setSelectedPolicy(policy)} /></article>)}</div></section>}<p className="quick-disclaimer">{result.disclaimer}</p></section>}
        <PolicyReviewDrawer policy={selectedPolicy ? quickPolicyToReview(selectedPolicy) : null} onClose={() => setSelectedPolicy(null)} />
      </div>
    </main>
  );
}
