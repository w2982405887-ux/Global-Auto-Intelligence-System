"use client";

import {
  AlertTriangle,
  ArrowLeft,
  Calculator,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  Database,
  Factory,
  Gauge,
  Info,
  LoaderCircle,
  TrendingDown,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  type CkdCalculationResult,
  calculateCkd,
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
const DECL_MODES = [
  { v: "CKD_WHOLE_KIT_WITH_RULING", l: "已取得整套归类裁定", d: "海关已确认整套 CKD 单一税号" },
  { v: "CKD_WHOLE_KIT_PENDING_RULING", l: "拟按整套申报（裁定未出）", d: "计划按整套归类，但尚未取得正式裁定" },
  { v: "CLASSIFICATION_PENDING", l: "尚未确定归类方式", d: "需进一步咨询海关归类意见" },
];
const CKD_POLICIES = [
  { v: "MY_CKD_IMPORT_SST_EXEMPTION", l: "CKD进口销售税豁免 (DG批准)", pt: null },
  { v: "MY_CKD_BEV_EXCISE_EXEMPTION_2027", l: "BEV消费税豁免 (至2027/12/31)", pt: "BEV" },
  { v: "MY_CKD_BEV_FINISHED_SST_EXEMPTION_2027", l: "BEV成车销售税豁免 (至2027/12/31)", pt: "BEV" },
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

export function MalaysiaCkdWorkspace({ embedded = false, onSnapshot }: ScenarioWorkspaceProps) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    effective_date: today,
    origin_country_iso2: "CN",
    powertrain: "BEV",
    displacement_cc: "",
    body_type: "SEDAN",
    // Business scope is fixed to passenger vehicles with four-wheel drive.
    // Keep this internal; it is intentionally not a user-facing filter.
    drive_type: "4WD_AWD",
    erev_architecture: "UNKNOWN",
    ckd_tariff_code: "",
    customs_value: "",
    declaration_mode: "CKD_WHOLE_KIT_PENDING_RULING",
    miti_ckd_ap_confirmed: false,
  });
  const [policies, setPolicies] = useState<string[]>([
    "MY_CKD_BEV_EXCISE_EXEMPTION_2027",
    "MY_CKD_BEV_FINISHED_SST_EXEMPTION_2027",
  ]);
  const [ratios, setRatios] = useState({ excise_value_ratio: "", sales_value_ratio: "" });
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CkdCalculationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPolicy, setSelectedPolicy] = useState<NonNullable<CkdCalculationResult["incentive_validation"]>["resolved"][number] | null>(null);

  const selPt = POWERTRAINS.find((item) => item.value === form.powertrain);
  const needDisp = selPt?.needsDisp ?? false;
  const needCode = form.declaration_mode === "CKD_WHOLE_KIT_WITH_RULING";
  const unresolvedErev = form.powertrain === "EREV" && form.erev_architecture === "UNKNOWN";
  const seriesOnlyErev = form.powertrain === "EREV" && form.erev_architecture === "SERIES_ONLY_ELECTRIC_WHEEL_TORQUE";
  const effectivePowertrain = form.powertrain === "EREV" && form.erev_architecture === "ENGINE_CAN_DRIVE_WHEELS_SPARK" ? "PHEV" : form.powertrain;
  const canCalc = !busy && (!needCode || form.ckd_tariff_code) && (!needDisp || form.displacement_cc) && !unresolvedErev && !seriesOnlyErev;

  useEffect(() => {
    onSnapshot?.(null);
  }, [form.effective_date, form.origin_country_iso2, form.powertrain, form.displacement_cc, form.body_type, form.erev_architecture, form.ckd_tariff_code, form.customs_value, form.declaration_mode, form.miti_ckd_ap_confirmed, policies, ratios.excise_value_ratio, ratios.sales_value_ratio, onSnapshot]);

  async function calc(nextRatios = ratios) {
    setBusy(true);
    setError(null);
    try {
      const data = await calculateCkd({
        effective_date: form.effective_date,
        origin_country_iso2: form.origin_country_iso2,
        powertrain: effectivePowertrain,
        displacement_cc: form.displacement_cc ? Number(form.displacement_cc) : null,
        body_type: form.body_type,
        drive_type: form.drive_type,
        ckd_tariff_code: form.ckd_tariff_code || null,
        customs_value: form.customs_value || null,
        declaration_mode: form.declaration_mode,
        miti_ckd_ap_confirmed: form.miti_ckd_ap_confirmed,
        selected_policy_codes: policies,
        excise_value_ratio: nextRatios.excise_value_ratio || null,
        sales_value_ratio: nextRatios.sales_value_ratio || null,
      });
      setResult(data);
      const hasFullCycle = Boolean(data.full_cycle_simulation.available && data.full_cycle_simulation.results?.length);
      const rates = hasFullCycle
        ? (data.full_cycle_simulation.results ?? []).map((item) => ({
            regime: item.regime_label,
            rate: item.simulated_full_cycle_rate,
            scope: "FULL_CHAIN" as const,
            complete: item.simulated_full_cycle_rate != null,
          }))
        : data.import_stage.import_effective_rates.map((item) => ({
            regime: item.regime_label,
            rate: item.effective_rate,
            scope: "IMPORT_STAGE" as const,
            complete: item.effective_rate != null,
          }));
      const missingItems = Array.from(new Set([
        ...data.local_assembly_stage.missing_for_complete_calculation,
        ...(!hasFullCycle ? data.full_cycle_simulation.required_inputs.map((item) => item.description) : []),
      ]));
      onSnapshot?.({
        countryIso2: "MY",
        countryName: "马来西亚",
        route: "CKD",
        title: "马来西亚 CKD 整套散件进口 + 本地组装",
        effectiveDate: form.effective_date,
        originCountryIso2: form.origin_country_iso2,
        powertrain: effectivePowertrain,
        status: hasFullCycle ? "COMPLETE" : rates.length > 0 ? "PARTIAL" : "BLOCKED",
        confidence: data.hs_classification ? "MEDIUM" : "LOW",
        scopeLabel: hasFullCycle ? "本地组装全流程模拟" : "仅进口环节",
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
    <main className={`ckd-page${embedded ? " scenario-workspace-embedded" : ""}`}>
      <div className="ckd-shell">
        <Link className="ckd-back" href="/"><ArrowLeft size={17} /> 返回全球决策</Link>
        <header className="ckd-hero">
          <div>
            <span className="ckd-eyebrow"><Factory size={14} /> CKD WHOLE-KIT IMPORT</span>
            <h1>马来西亚 CKD 整套散件进口 + 本地组装税务分析</h1>
            <p>与 CBU 不同，CKD 消费税不在进口环节征收。进口关税按制度展示，进口销售税为条件性豁免（需 DG 批准），消费税和成车销售税在本地组装阶段征收。所有数值为标准化税基(100)。</p>
          </div>
          <span className="ckd-db-state"><Database size={17} /> 实时连接政策数据库</span>
        </header>

        <section className="ckd-input-card">
          <div className="ckd-input-grid">
            <label><span><CalendarDays size={15} /> 进口日期</span><input type="date" value={form.effective_date} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} /><small>匹配当期有效税率</small></label>
            <label><span><TrendingDown size={15} /> 原产国</span><select value={form.origin_country_iso2} onChange={(e) => setForm({ ...form, origin_country_iso2: e.target.value })}>{ORIGINS.map((c) => <option key={c} value={c}>{c}</option>)}</select><small>决定 MFN / ACFTA / RCEP</small></label>
            <label><span><Zap size={15} /> 动力类型</span><select value={form.powertrain} onChange={(e) => { const pt = e.target.value; const needs = POWERTRAINS.find((p) => p.value === pt)?.needsDisp; setForm({ ...form, powertrain: pt, displacement_cc: needs ? form.displacement_cc : "" }); }}>{POWERTRAINS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}</select><small>默认新车乘用车</small></label>
            <label><span><Gauge size={15} /> 排量 (cc){!needDisp && " — 纯电无需"}</span>{needDisp ? <select value={form.displacement_cc} onChange={(e) => setForm({ ...form, displacement_cc: e.target.value })}><option value="">请选择</option>{DISPS.map((d) => <option key={d} value={d}>{d}cc</option>)}</select> : <input type="text" value="不适用" disabled className="ckd-disabled-input" />}<small>{needDisp ? "本地消费税按排量和车型核定" : "BEV/FCEV无需排量"}</small></label>
            <label className="ckd-full-width"><span>CKD PDK 税号（10位）{needCode ? " — 必填" : " — 可选"}</span><input type="text" value={form.ckd_tariff_code} onChange={(e) => setForm({ ...form, ckd_tariff_code: e.target.value })} placeholder="例：8703801700" maxLength={10} className="ckd-tax-code-input" /><small>CKD 税号与 CBU 不同，是否可用取决于实际海关归类裁定。</small></label>
            <label><span>实际进口申报方式</span><select value={form.declaration_mode} onChange={(e) => setForm({ ...form, declaration_mode: e.target.value })}>{DECL_MODES.map((dm) => <option key={dm.v} value={dm.v}>{dm.l}</option>)}</select><small>{DECL_MODES.find((d) => d.v === form.declaration_mode)?.d}</small></label>
            <label className="ckd-checkbox-label"><span>MITI CKD AP</span><div className="ckd-checkbox-row"><input type="checkbox" checked={form.miti_ckd_ap_confirmed} onChange={(e) => setForm({ ...form, miti_ckd_ap_confirmed: e.target.checked })} /><span>已取得 MITI CKD AP（进口许可证，≠ 税收减免）</span></div></label>
            <label><span>车身/用途细分</span><select value={form.body_type} onChange={(e) => setForm({ ...form, body_type: e.target.value })}>{BODY_TYPES.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}</select><small>用于继续细分马来西亚10位PDK税号</small></label>
            {form.powertrain === "EREV" && <label className="ckd-full-width"><span>EREV 增程结构判定</span><select value={form.erev_architecture} onChange={(e) => setForm({ ...form, erev_architecture: e.target.value })}>{EREV_ARCHITECTURES.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}</select><small>纯电续航不是马来西亚消费税分档条件；关键是发动机是否参与推进。</small></label>}
            {seriesOnlyErev && <div className="ckd-full-width ckd-error"><CircleAlert size={17} />纯串联 EREV 暂不自动套用 PHEV 税号，建议取得海关预裁定后再计算。</div>}
          </div>

          <details className="ckd-advanced">
            <summary><Info size={15} /> 优惠政策与高级选项</summary>
            <div className="ckd-advanced-grid">
              <div><span>已取得或拟适用的优惠政策</span><div className="ckd-policy-checks">{CKD_POLICIES.filter((p) => !p.pt || p.pt === form.powertrain).map((p) => <label key={p.v} className="ckd-check-row"><input type="checkbox" checked={policies.includes(p.v)} onChange={(e) => setPolicies(e.target.checked ? [...policies, p.v] : policies.filter((x) => x !== p.v))} /><span>{p.l}</span></label>)}</div><small>CKD进口销售税豁免需 DG 批准；AP 不自动豁免税收。</small></div>
              <label><span>海关价值 (MYR) — 可选</span><input type="number" min="0" value={form.customs_value} onChange={(e) => setForm({ ...form, customs_value: e.target.value })} placeholder="留空使用标准化税基100" /></label>
            </div>
          </details>

          {error && <div className="ckd-error"><CircleAlert size={17} />{error}</div>}
          <button type="button" className="ckd-calculate-btn" disabled={!canCalc} onClick={() => calc()}>{busy ? <><LoaderCircle className="spin" size={18} /> 计算中…</> : <><Calculator size={18} /> 查询 CKD 税号并计算进口环节税负</>}</button>
        </section>

        {result && (
          <section className="ckd-results">
            {result.hs_classification && <div className="ckd-hs-banner"><div className="ckd-hs-code"><span>匹配 CKD 税号</span><strong>{result.hs_classification.national_tariff_code}</strong><small>HS6: {result.hs_classification.hs6_code} · {result.hs_classification.tariff_description}</small></div><div className="ckd-hs-meta"><span className="ckd-verified-badge"><CheckCircle2 size={14} /> {result.hs_classification.verification_status}</span><small>来源：{result.hs_classification.source_code}<br />{result.classification_note}</small></div></div>}
            <section className="ckd-section"><header className="ckd-section-header"><div><span className="ckd-section-kicker">STAGE 1 — IMPORT</span><h2>进口环节 — 进口关税 + 进口销售税</h2></div></header><div className="ckd-duty-grid">{result.import_stage.import_duty_options.map((opt) => <div key={`${opt.agreement_code ?? "MFN"}-${opt.national_tariff_code}`} className={`ckd-duty-card ${regimeClr(opt.agreement_code ?? "MFN")}`}><div className="ckd-duty-badge">{opt.agreement_code ?? "MFN"}</div><div className="ckd-duty-rate">{fmtPct(opt.rate)}</div><div className="ckd-duty-detail"><span>{opt.tariff_description}</span><code>{opt.national_tariff_code}</code></div><div className="ckd-duty-amount">每100: {fmtPer100(opt.per_100)}</div>{opt.eligibility_note && <div className="ckd-duty-eligibility"><Info size={14} /><span>{opt.eligibility_note}</span></div>}</div>)}</div><div className="ckd-import-eff"><span>进口环节综合税率：</span>{result.import_stage.import_effective_rates.map((r) => <span key={r.regime_label} className={`ckd-eff-chip ${regimeClr(r.regime_label)}`}>{r.regime_label}：{fmtPct(r.effective_rate)}</span>)}</div></section>
            <section className="ckd-section"><header className="ckd-section-header"><div><span className="ckd-section-kicker">STAGE 2 — LOCAL ASSEMBLY</span><h2>本地组装成车环节</h2></div></header><div className="ckd-domestic-grid"><div className="ckd-domestic-card excise"><div className="ckd-domestic-badge">消费税 EXCISE</div><div className="ckd-domestic-rate">{fmtPct(result.local_assembly_stage.excise_duty.applied_rate)}</div><div className="ckd-domestic-stage-badge not-at-import"><AlertTriangle size={13} /> 不在进口环节征收</div></div><div className="ckd-domestic-card sst"><div className="ckd-domestic-badge">成车销售税 FINISHED VEHICLE SST</div><div className="ckd-domestic-rate">{fmtPct(result.local_assembly_stage.finished_vehicle_sales_tax.applied_rate)}</div><div className="ckd-domestic-stage-badge not-at-import"><AlertTriangle size={13} /> 与进口销售税是两个独立税种</div></div></div>{result.local_assembly_stage.missing_for_complete_calculation.length > 0 && <div className="ckd-missing-local"><CircleAlert size={16} /><div><strong>全流程税负暂不可计算</strong><ul>{result.local_assembly_stage.missing_for_complete_calculation.map((m, i) => <li key={i}>{m}</li>)}</ul></div></div>}</section>
            <section className="ckd-section"><header className="ckd-section-header"><div><span className="ckd-section-kicker">STAGE 3 — SIMULATION</span><h2>全流程模拟（需补充估值系数）</h2></div></header>{!result.full_cycle_simulation.available && <div className="ckd-ratio-inputs"><p className="ckd-ratio-hint">{result.full_cycle_simulation.message || "缺少估值系数，无法计算全流程税负率。"}</p><div className="ckd-ratio-grid"><label><span>消费税核定价值 / 进口价值</span><input type="number" min="0" step="0.01" placeholder="例：1.30" value={ratios.excise_value_ratio} onChange={(e) => setRatios({ ...ratios, excise_value_ratio: e.target.value })} /></label><label><span>销售税计税价值 / 进口价值</span><input type="number" min="0" step="0.01" placeholder="例：1.45" value={ratios.sales_value_ratio} onChange={(e) => setRatios({ ...ratios, sales_value_ratio: e.target.value })} /></label></div><button type="button" className="ckd-recalc-btn" disabled={!ratios.excise_value_ratio || !ratios.sales_value_ratio || busy} onClick={() => calc(ratios)}>补充数据并重新计算</button></div>}{result.full_cycle_simulation.available && result.full_cycle_simulation.results && <div className="ckd-full-cycle-grid">{result.full_cycle_simulation.results.map((r) => <div key={r.regime_label} className="ckd-full-cycle-card"><div className={`ckd-full-cycle-badge ${regimeClr(r.regime_label)}`}>{r.regime_label}</div><div className="ckd-full-cycle-stages"><div className="ckd-stage-col"><span>进口阶段</span><strong>{fmtPct(r.import_effective_rate)}</strong></div><div className="ckd-stage-col total"><span>全流程模拟</span><strong>{fmtPct(r.simulated_full_cycle_rate)}</strong></div></div></div>)}</div>}</section>
            {result.incentive_validation?.resolved?.length ? <section className="ckd-section policy-review-section"><header className="ckd-section-header"><div><span className="ckd-section-kicker">POLICY REVIEW</span><h2>匹配政策与出处</h2></div><small>点击政策查看说明、条件和官方来源</small></header><div className="policy-review-list">{result.incentive_validation.resolved.map((policy) => <article key={policy.program_code}><strong>{policy.program_name_cn}</strong><span>{policy.status}</span><PolicyReviewTrigger onClick={() => setSelectedPolicy(policy)} /></article>)}</div></section> : null}
            {result.notes.length > 0 && <div className="ckd-notes"><Info size={16} /><ul>{result.notes.map((note, index) => <li key={index}>{note}</li>)}</ul></div>}
            <p className="ckd-disclaimer">{result.disclaimer}</p>
          </section>
        )}

        <PolicyReviewDrawer policy={selectedPolicy ? resolvedPolicyToReview(selectedPolicy) : null} onClose={() => setSelectedPolicy(null)} />

        {!result && !busy && <div className="ckd-empty-hint"><Factory size={40} /><h3>输入 CKD 信息后点击计算</h3><p>系统会分进口环节和本地组装环节展示马来西亚 CKD 税负。</p></div>}
      </div>
    </main>
  );
}

export default function CkdPage() {
  return <MalaysiaCkdWorkspace />;
}
