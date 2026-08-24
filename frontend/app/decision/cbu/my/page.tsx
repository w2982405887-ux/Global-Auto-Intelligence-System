"use client";

import {
  ArrowLeft,
  Calculator,
  CalendarDays,
  CarFront,
  CheckCircle2,
  CircleAlert,
  Database,
  Gauge,
  Info,
  LoaderCircle,
  TrendingDown,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  type CbuCalculationResult,
  calculateCbu,
} from "../../../lib/api";
import { PolicyReviewDrawer, PolicyReviewTrigger, resolvedPolicyToReview } from "../../../components/PolicyReviewDrawer";
import type { ScenarioWorkspaceProps } from "../../ScenarioWorkspace";

const POWERTRAINS = [
  { value: "ICE_GASOLINE", label: "ICE 汽油", needsDisp: true },
  { value: "ICE_DIESEL", label: "ICE 柴油", needsDisp: true },
  { value: "HEV", label: "HEV 油电混合", needsDisp: true },
  { value: "PHEV", label: "PHEV 插电混动", needsDisp: true },
  { value: "EREV", label: "EREV 增程式", needsDisp: true },
  { value: "BEV", label: "BEV 纯电动", needsDisp: false },
  { value: "FCEV", label: "FCEV 氢燃料", needsDisp: false },
];
const ORIGINS = ["CN", "TH", "ID", "VN", "JP", "KR", "DE", "MY", "OTHER"];
const DISPS = [1000, 1200, 1500, 1800, 2000, 2500, 3000, 3500];
const BODY_TYPES = [
  { value: "SEDAN", label: "Sedan / 轿车" },
  { value: "SUV", label: "SUV / 越野或运动型" },
  { value: "MPV", label: "MPV / 多用途" },
  { value: "HATCHBACK", label: "Hatchback / 两厢" },
  { value: "COUPE", label: "Coupe / 轿跑" },
  { value: "WAGON", label: "Station Wagon / 旅行车" },
  { value: "OTHER", label: "Other motor car / 其他乘用车" },
];
const EREV_ARCHITECTURES = [
  { value: "UNKNOWN", label: "不确定 / 需要先判断" },
  { value: "ENGINE_CAN_DRIVE_WHEELS_SPARK", label: "汽油增程器可机械驱动车轮 / 按 PHEV 口径" },
  { value: "SERIES_ONLY_ELECTRIC_WHEEL_TORQUE", label: "发动机仅发电，车轮只由电机驱动 / 建议预裁定" },
];
const IN_POLICIES = [
  { value: "MY_CBU_BEV_EXCISE_EXEMPTION_2027", label: "BEV消费税豁免(至2027/12/31)", pt: "BEV" },
  { value: "MY_CBU_BEV_SST_EXEMPTION_2027", label: "BEV销售税豁免(至2027/12/31)", pt: "BEV" },
];

function fmtPct(v: string | null | undefined): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}
function fmtPer100(v: string | null | undefined): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return n.toFixed(2);
}
function regimeClr(label: string | null | undefined) {
  if (label === "MFN") return "mfn";
  if (label === "ACFTA") return "acfta";
  if (label === "RCEP") return "rcep";
  return "fta";
}

export function MalaysiaCbuWorkspace({ embedded = false, onSnapshot }: ScenarioWorkspaceProps) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    effective_date: today,
    origin_country_iso2: "CN",
    powertrain: "BEV",
    displacement_cc: "",
    customs_value: "",
    body_type: "SEDAN",
    // Business scope is fixed to passenger vehicles with four-wheel drive.
    // Keep this internal; it is intentionally not a user-facing filter.
    drive_type: "4WD_AWD",
    erev_architecture: "UNKNOWN",
  });
  const [policies, setPolicies] = useState<string[]>([
    "MY_CBU_BEV_EXCISE_EXEMPTION_2027",
    "MY_CBU_BEV_SST_EXEMPTION_2027",
  ]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CbuCalculationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPolicy, setSelectedPolicy] = useState<NonNullable<CbuCalculationResult["incentive_validation"]>["resolved"][number] | null>(null);

  const selPt = POWERTRAINS.find((item) => item.value === form.powertrain);
  const needDisp = selPt?.needsDisp ?? false;
  const unresolvedErev = form.powertrain === "EREV" && form.erev_architecture === "UNKNOWN";
  const seriesOnlyErev = form.powertrain === "EREV" && form.erev_architecture === "SERIES_ONLY_ELECTRIC_WHEEL_TORQUE";
  const effectivePowertrain = form.powertrain === "EREV" && form.erev_architecture === "ENGINE_CAN_DRIVE_WHEELS_SPARK" ? "PHEV" : form.powertrain;

  useEffect(() => {
    onSnapshot?.(null);
  }, [form.effective_date, form.origin_country_iso2, form.powertrain, form.displacement_cc, form.customs_value, form.body_type, form.erev_architecture, policies, onSnapshot]);

  async function calc() {
    setBusy(true);
    setError(null);
    try {
      const data = await calculateCbu({
        effective_date: form.effective_date,
        origin_country_iso2: form.origin_country_iso2,
        powertrain: effectivePowertrain,
        displacement_cc: form.displacement_cc ? Number(form.displacement_cc) : null,
        body_type: form.body_type,
        drive_type: form.drive_type,
        customs_value: form.customs_value || null,
        selected_policy_codes: policies,
      });
      setResult(data);
      const rates = data.combined_results.map((item) => ({
        regime: item.regime_label,
        rate: item.effective_tax_rate,
        scope: "FULL_CHAIN" as const,
        complete: item.is_complete,
      }));
      const missingItems = Array.from(new Set(data.combined_results.flatMap((item) => item.unknown_items)));
      onSnapshot?.({
        countryIso2: "MY",
        countryName: "马来西亚",
        route: "CBU",
        title: "马来西亚 CBU 整车进口",
        effectiveDate: form.effective_date,
        originCountryIso2: form.origin_country_iso2,
        powertrain: effectivePowertrain,
        status: rates.some((item) => item.complete) ? "COMPLETE" : rates.length > 0 ? "PARTIAL" : "BLOCKED",
        confidence: data.hs_classification ? "HIGH" : "LOW",
        scopeLabel: "整车进口完整税链",
        tariffCodes: data.hs_classification ? [data.hs_classification.national_tariff_code] : [],
        rates,
        missingItems,
        notes: data.notes,
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "计算失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={`cbu-page${embedded ? " scenario-workspace-embedded" : ""}`}>
      <div className="cbu-shell">
        <Link className="cbu-back" href="/"><ArrowLeft size={17} /> 返回全球决策</Link>
        <header className="cbu-hero">
          <div>
            <span className="cbu-eyebrow"><Calculator size={14} /> CBU VEHICLE IMPORT</span>
            <h1>马来西亚 CBU 整车进口税务分析</h1>
            <p>填入车辆属性，系统按日期、原产国、动力类型和车辆细分匹配马来西亚 HS/PDK 税号，并计算进口关税、消费税、销售税和综合税负。</p>
          </div>
          <span className="cbu-db-state"><Database size={17} /> 实时连接政策数据库</span>
        </header>

        <section className="cbu-input-card">
          <div className="cbu-input-grid">
            <label><span><CalendarDays size={15} /> 进口日期</span><input type="date" value={form.effective_date} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} /><small>匹配当期有效税率</small></label>
            <label><span><TrendingDown size={15} /> 原产国</span><select value={form.origin_country_iso2} onChange={(e) => setForm({ ...form, origin_country_iso2: e.target.value })}>{ORIGINS.map((c) => <option key={c} value={c}>{c}</option>)}</select><small>决定 MFN / ACFTA / RCEP</small></label>
            <label><span><Zap size={15} /> 动力类型</span><select value={form.powertrain} onChange={(e) => { const pt = e.target.value; const needs = POWERTRAINS.find((p) => p.value === pt)?.needsDisp; setForm({ ...form, powertrain: pt, displacement_cc: needs ? form.displacement_cc : "" }); }}>{POWERTRAINS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}</select><small>默认新车乘用车</small></label>
            <label><span><Gauge size={15} /> 排量 (cc){!needDisp && " — 纯电无需"}</span>{needDisp ? <select value={form.displacement_cc} onChange={(e) => setForm({ ...form, displacement_cc: e.target.value })}><option value="">请选择</option>{DISPS.map((d) => <option key={d} value={d}>{d}cc</option>)}</select> : <input type="text" value="不适用" disabled className="cbu-disabled-input" />}<small>{needDisp ? "消费税按排量和车型分档" : "BEV/FCEV无需排量"}</small></label>
            <label><span>车身/用途细分</span><select value={form.body_type} onChange={(e) => setForm({ ...form, body_type: e.target.value })}>{BODY_TYPES.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}</select><small>用于继续细分马来西亚10位PDK税号</small></label>
            {form.powertrain === "EREV" && <label className="cbu-full-width"><span>EREV 增程结构判定</span><select value={form.erev_architecture} onChange={(e) => setForm({ ...form, erev_architecture: e.target.value })}>{EREV_ARCHITECTURES.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}</select><small>纯电续航不是马来西亚消费税分档条件；关键是发动机是否参与推进。</small></label>}
            {seriesOnlyErev && <div className="cbu-full-width cbu-error"><CircleAlert size={17} />纯串联 EREV 暂不自动套用 PHEV 税号，建议取得海关预裁定后再计算。</div>}
          </div>

          <details className="cbu-advanced">
            <summary><Info size={15} /> 优惠政策与高级选项</summary>
            <div className="cbu-advanced-grid">
              <div>
                <span>已取得或拟适用的优惠政策</span>
                <div className="cbu-policy-checks">
                  {IN_POLICIES.filter((p) => p.pt === form.powertrain || !p.pt).map((p) => (
                    <label key={p.value} className="cbu-check-row"><input type="checkbox" checked={policies.includes(p.value)} onChange={(e) => setPolicies(e.target.checked ? [...policies, p.value] : policies.filter((x) => x !== p.value))} /><span>{p.label}</span></label>
                  ))}
                  {IN_POLICIES.every((p) => p.pt !== form.powertrain) && <small>当前动力类型无可选优惠政策</small>}
                </div>
              </div>
              <label><span>海关价值 (MYR) — 可选</span><input type="number" min="0" value={form.customs_value} onChange={(e) => setForm({ ...form, customs_value: e.target.value })} placeholder="留空使用标准化税基100" /><small>不填则显示每100税基的比例结果</small></label>
            </div>
          </details>

          {error && <div className="cbu-error"><CircleAlert size={17} />{error}</div>}
          <button type="button" className="cbu-calculate-btn" disabled={busy || (needDisp && !form.displacement_cc) || unresolvedErev || seriesOnlyErev} onClick={calc}>{busy ? <><LoaderCircle className="spin" size={18} /> 计算中…</> : <><Calculator size={18} /> 筛选政策、税号并计算综合税率</>}</button>
        </section>

        {result && (
          <section className="cbu-results">
            {result.hs_classification && <div className="cbu-hs-banner"><div className="cbu-hs-code"><span>匹配税号</span><strong>{result.hs_classification.national_tariff_code}</strong><small>HS6: {result.hs_classification.hs6_code} · {result.hs_classification.tariff_description}</small></div><div className="cbu-hs-meta"><span className="cbu-verified-badge"><CheckCircle2 size={14} /> {result.hs_classification.verification_status}</span><small>来源：{result.hs_classification.source_code}</small></div></div>}
            <section className="cbu-section"><header className="cbu-section-header"><div><span className="cbu-section-kicker">IMPORT DUTY</span><h2>进口关税</h2></div></header><div className="cbu-duty-grid">{result.import_duty_options.map((opt) => <div key={`${opt.agreement_code ?? "MFN"}-${opt.national_tariff_code}`} className={`cbu-duty-card ${regimeClr(opt.agreement_code ?? "MFN")}`}><div className="cbu-duty-badge">{opt.agreement_code ?? "MFN"}</div><div className="cbu-duty-rate">{fmtPct(opt.rate)}</div><div className="cbu-duty-detail"><span>{opt.tariff_description}</span><code>{opt.national_tariff_code}</code></div><div className="cbu-duty-amount">每100: {fmtPer100(opt.per_100)}</div>{opt.eligibility_note && <div className="cbu-duty-eligibility"><Info size={14} /><span>{opt.eligibility_note}</span></div>}</div>)}</div></section>
            <section className="cbu-section"><header className="cbu-section-header"><div><span className="cbu-section-kicker">COMPREHENSIVE</span><h2>综合税负对比</h2></div></header><div className="cbu-combined-grid">{result.combined_results.map((cr) => <div key={cr.regime_label} className={`cbu-combined-card ${cr.is_complete ? "" : "incomplete"}`}><div className={`cbu-combined-badge ${regimeClr(cr.regime_label)}`}>{cr.regime_label}</div><div className="cbu-tax-lines"><div className="cbu-tax-line"><span>进口关税</span><span>{fmtPct(cr.import_duty_rate)}</span><strong>{fmtPer100(cr.import_duty_per_100)}</strong></div><div className="cbu-tax-line"><span>消费税</span><span>{fmtPct(cr.excise_duty_rate)}</span><strong>{fmtPer100(cr.excise_duty_per_100)}</strong></div><div className="cbu-tax-line"><span>销售税</span><span>{fmtPct(cr.sales_tax_rate)}</span><strong>{fmtPer100(cr.sales_tax_per_100)}</strong></div><div className="cbu-tax-line total"><span>综合税负</span><span>{fmtPct(cr.effective_tax_rate)}</span><strong>{fmtPer100(cr.total_per_100)}</strong></div></div>{!cr.is_complete && <div className="cbu-unknown"><CircleAlert size={15} /><span>缺失：{cr.unknown_items.join("、")}</span></div>}</div>)}</div></section>
            {result.incentive_validation?.resolved?.length ? <section className="cbu-section policy-review-section"><header className="cbu-section-header"><div><span className="cbu-section-kicker">POLICY REVIEW</span><h2>匹配政策与出处</h2></div><small>点击政策查看说明、条件和官方来源</small></header><div className="policy-review-list">{result.incentive_validation.resolved.map((policy) => <article key={policy.program_code}><strong>{policy.program_name_cn}</strong><span>{policy.status}</span><PolicyReviewTrigger onClick={() => setSelectedPolicy(policy)} /></article>)}</div></section> : null}
            {result.notes.length > 0 && <div className="cbu-notes"><Info size={16} /><ul>{result.notes.map((note, index) => <li key={index}>{note}</li>)}</ul></div>}
            <p className="cbu-disclaimer">{result.disclaimer}</p>
          </section>
        )}

        <PolicyReviewDrawer policy={selectedPolicy ? resolvedPolicyToReview(selectedPolicy) : null} onClose={() => setSelectedPolicy(null)} />

        {!result && !busy && <div className="cbu-empty-hint"><CarFront size={40} /><h3>填入车辆信息后点击计算</h3><p>系统会筛选适用政策、候选税号和税率，并输出马来西亚 CBU 综合税负。</p></div>}
      </div>
    </main>
  );
}

export default function CbuPage() {
  return <MalaysiaCbuWorkspace />;
}
