"use client";

import { ArrowLeft, Calculator, CalendarDays, CircleAlert, Database, Factory, Gauge, Info, LoaderCircle, PackageSearch, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  type QuickEstimatePath,
  type QuickEstimateResult,
  createQuickEstimate,
} from "../../../lib/api";
import {
  autoSelectCandidateCode,
  factLabel,
  formatVietnameseCandidate,
  type VietnamTariffCandidate,
} from "../../../lib/vietnamTariff";
import { PolicyReviewDrawer, PolicyReviewTrigger, quickPolicyToReview } from "../../../components/PolicyReviewDrawer";
import type { ScenarioWorkspaceProps } from "../../ScenarioWorkspace";

const ORIGINS = [
  { code: "CN", label: "中国 · CN" },
  { code: "TH", label: "泰国 · TH" },
  { code: "ID", label: "印度尼西亚 · ID" },
  { code: "VN", label: "越南 · VN" },
  { code: "JP", label: "日本 · JP" },
  { code: "KR", label: "韩国 · KR" },
  { code: "AU", label: "澳大利亚 · AU" },
  { code: "NZ", label: "新西兰 · NZ" },
  { code: "ZZ", label: "其他/待确认" },
];

const POWERTRAINS = [
  { value: "ICE_GASOLINE", label: "ICE 汽油" },
  { value: "ICE_DIESEL", label: "ICE 柴油" },
  { value: "HEV", label: "HEV 油电混合" },
  { value: "PHEV", label: "PHEV 插电混动" },
  { value: "EREV", label: "EREV 增程式" },
  { value: "BEV", label: "BEV 纯电动" },
  { value: "FCEV", label: "FCEV 氢燃料" },
];

const COMPONENTS_BY_POWERTRAIN: Record<string, string[]> = {
  ICE_GASOLINE: ["汽油发动机", "变速箱/减速器", "车身", "底盘", "悬架/车桥", "转向", "制动", "轮胎/轮毂", "热管理", "线束", "座椅", "玻璃", "车灯", "仪表/显示屏", "安全气囊/安全带"],
  ICE_DIESEL: ["柴油发动机", "变速箱/减速器", "车身", "底盘", "悬架/车桥", "转向", "制动", "轮胎/轮毂", "热管理", "线束", "座椅", "玻璃", "车灯", "仪表/显示屏", "安全气囊/安全带"],
  HEV: ["发动机", "动力电池", "电机", "电控", "变速箱/减速器", "车身", "底盘", "悬架/车桥", "转向", "制动", "轮胎/轮毂", "热管理", "线束", "座椅", "玻璃", "车灯", "仪表/显示屏", "安全气囊/安全带"],
  PHEV: ["发动机", "动力电池", "电机", "电控", "变速箱/减速器", "车身", "底盘", "悬架/车桥", "转向", "制动", "轮胎/轮毂", "热管理", "线束", "座椅", "玻璃", "车灯", "仪表/显示屏", "安全气囊/安全带"],
  EREV: ["发动机/增程器", "动力电池", "电机", "电控", "减速器", "车身", "底盘", "悬架/车桥", "转向", "制动", "轮胎/轮毂", "热管理", "线束", "座椅", "玻璃", "车灯", "仪表/显示屏", "安全气囊/安全带"],
  BEV: ["动力电池", "电机", "电控", "减速器", "车身", "底盘", "悬架/车桥", "转向", "制动", "轮胎/轮毂", "热管理", "线束", "座椅", "玻璃", "车灯", "仪表/显示屏", "安全气囊/安全带"],
  FCEV: ["电机", "电控", "小容量动力/缓冲电池", "车身", "底盘", "悬架/车桥", "转向", "制动", "轮胎/轮毂", "热管理", "线束", "座椅", "玻璃", "车灯", "仪表/显示屏", "安全气囊/安全带"],
};

function rateText(value: string | null | undefined) {
  if (value == null || value === "") return "待确认";
  const n = Number(value);
  if (Number.isNaN(n)) return "待确认";
  return `${(n * 100).toFixed(2).replace(/\.00$/, "")}%`;
}

function moneyText(value: string | null | undefined) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return n.toFixed(2).replace(/\.00$/, "");
}

function confidenceText(value: string | null | undefined) {
  return value === "HIGH" ? "高" : value === "MEDIUM" ? "中" : "低";
}

function dutyLines(item: QuickEstimatePath | undefined) {
  return item?.incentive.tax_lines.filter((line) => line.tax.startsWith("IMPORT_DUTY")) ?? [];
}

function componentMatches(component: string, matchedNames: Set<string>) {
  if (matchedNames.has(component)) return true;
  if (component === "发动机" || component === "发动机/增程器") return matchedNames.has("汽油发动机") || matchedNames.has("柴油发动机");
  if (component === "减速器") return matchedNames.has("变速箱/减速器");
  if (component === "小容量动力/缓冲电池") return matchedNames.has("动力电池");
  return false;
}

function candidateCodeMap(path: QuickEstimatePath | undefined, displacement: string, engineAssembly: "COMPLETE" | "PARTS" | "UNKNOWN") {
  const codes: Record<string, string> = {};
  const notes: Record<string, string> = {};
  if (!path?.component_candidates) return { codes, notes };
  for (const component of path.component_candidates) {
    const result = autoSelectCandidateCode(
      component.ccu_code,
      component.candidates as VietnamTariffCandidate[],
      displacement,
      engineAssembly,
    );
    if (result.code) codes[component.ccu_code] = result.code;
    if (result.reason) notes[component.ccu_code] = result.reason;
  }
  return { codes, notes };
}

function DecisionSummary({ path }: { path: QuickEstimatePath }) {
  const candidates = path.component_candidates ?? [];
  const candidateCount = candidates.filter((item) => item.candidates.length > 0).length;
  const selectedCount = path.incentive.matched_component_count ?? 0;
  const expectedCount = path.incentive.expected_component_count ?? candidates.length;
  const completion = expectedCount > 0 ? Math.round((selectedCount / expectedCount) * 100) : 0;
  const hasRate = path.incentive.effective_tax_rate != null;
  const risk = path.status === "CLASSIFICATION_SELECTION_REQUIRED" ? "中：需逐件确认税号" : "中：仍需核验归类依据";
  const actionableMissing = path.missing_items.filter((item) => !item.includes("本地组装后") && !item.includes("98.49"));
  return (
    <section className="vn-decision-summary">
      <div className="vn-decision-summary-header">
        <div>
          <span className="ckd-section-kicker">01 / DECISION SUMMARY</span>
          <h2>越南 CKD 出口方案判断</h2>
          <p>先回答“能不能做、优先走哪条路径”，再展开税号和政策依据。</p>
        </div>
        <span className={`vn-decision-status ${hasRate ? "ready" : "pending"}`}>
          {hasRate ? "已完成主要部件税号选择" : "尚未形成可比较税负"}
        </span>
      </div>
      <div className="vn-decision-metrics">
        <article><span>建议进口模式</span><strong>Multi-HS 零件分别归类</strong><small>整车归类风险需另行预裁定</small></article>
        <article><span>最优关税制度</span><strong>{path.incentive.regime ?? "ACFTA / RCEP 候选"}</strong><small>{path.incentive.regime ? "已按所选税号计算" : "原产地证明和逐件税号仍需确认"}</small></article>
        <article><span>CKD进口关税</span><strong>{rateText(path.incentive.effective_tax_rate)}</strong><small>{hasRate ? "已选税号加权结果" : "未选齐最终越南税号"}</small></article>
        <article><span>归类完成度</span><strong>{selectedCount}/{expectedCount}（{completion}%）</strong><small>这不是税负置信度，只表示税号选择进度</small></article>
      </div>
      <div className="vn-decision-compare">
        <div><span>与 CBU 相比</span><strong>待补充越南 CBU 10 位税号</strong><small>系统不自动替 CBU 选择整车税号</small></div>
        <div><span>归类风险</span><strong>{risk}</strong><small>同批散件若具备整车基本特征，需 Customs Ruling</small></div>
        <div><span>当前下一步</span><strong>{candidateCount}/{candidates.length} 类已有候选</strong><small>{actionableMissing.length > 0 ? `优先补齐：${actionableMissing.slice(0, 2).join("、")}` : "补充零件价值占比后再比较方案"}</small></div>
      </div>
      <div className="vn-decision-actions">
        <Link href="/decision/cbu/vn">去选择越南 CBU 税号，形成对照</Link>
        <span>全链条视图已列出这些缺口；未知税种不会被当作零税率</span>
      </div>
    </section>
  );
}

function chainStatusText(status: string | undefined) {
  if (status === "KNOWN_PARTIAL") return "已计入部分税额";
  if (status === "PARTIAL") return "部分可计算";
  if (status === "NOT_MODELED") return "尚未建模";
  if (status === "BLOCKED") return "缺少税号/税率";
  return "需补充条件";
}

function chainStatusClass(status: string | undefined) {
  if (status === "KNOWN_PARTIAL" || status === "PARTIAL") return "known";
  if (status === "NOT_MODELED") return "unmodeled";
  return "blocked";
}

function FullTaxChain({ path }: { path: QuickEstimatePath }) {
  const chain = path.tax_chain;
  if (!chain) return null;
  const knownRate = chain.known_effective_rate;
  const knownAmount = chain.known_tax_amount;
  return (
    <section className="ckd-section vn-tax-chain-section">
      <div className="ckd-section-header">
        <div>
          <span className="ckd-section-kicker">02 / FULL TAX CHAIN</span>
          <h2>全链条税负视图</h2>
        </div>
        <p>中国出口 → 越南进口 → 越南组装 → 越南销售。只把已经有依据的税额纳入结果，未知税种不会被当成零税率。</p>
      </div>
      <div className="vn-tax-chain-kpis">
        <article><span>当前已知税额</span><strong>{moneyText(knownAmount)}</strong><small>标准化进口件税基 {moneyText(chain.base_value)}</small></article>
        <article><span>已知进口关税率</span><strong>{rateText(knownRate)}</strong><small>仅代表已匹配主要部件，不是完整综合税率</small></article>
        <article><span>全链条状态</span><strong>{chainStatusText(chain.status)}</strong><small>现金税负：{chain.cash_tax_outlay == null ? "待补充" : moneyText(chain.cash_tax_outlay)}</small></article>
        <article><span>不可回收税负率</span><strong>{chain.non_recoverable_tax_rate == null ? "待补充" : rateText(chain.non_recoverable_tax_rate)}</strong><small>VAT抵扣与本地税基尚未确认</small></article>
      </div>
      <div className="vn-tax-chain-flow">
        {chain.nodes.map((node, index) => (
          <div className="vn-tax-chain-node-wrap" key={node.stage_code}>
            <article className={`vn-tax-chain-node ${chainStatusClass(node.status)}`}>
              <div className="vn-tax-chain-node-head">
                <strong>{node.stage_name}</strong>
                <span>{chainStatusText(node.status)}</span>
              </div>
              <div className="vn-tax-chain-node-rate">
                {node.known_effective_rate != null ? rateText(node.known_effective_rate) : "待补充"}
                {node.known_tax_amount != null && <small>已知税额 {moneyText(node.known_tax_amount)}</small>}
              </div>
              {node.tax_lines.length > 0 && (
                <div className="vn-tax-chain-lines">
                  {node.tax_lines.map((line) => (
                    <div key={`${node.stage_code}-${line.tax}`}>
                      <span>{line.tax.replace("IMPORT_DUTY:", "进口关税 · ")}</span>
                      <em>{line.rate != null ? rateText(line.rate) : "待建模"}</em>
                    </div>
                  ))}
                </div>
              )}
              <small className="vn-tax-chain-note">{node.note}</small>
              {node.missing_fields.length > 0 && <details className="vn-tax-chain-missing"><summary>查看缺失条件（{node.missing_fields.length}）</summary><ul>{node.missing_fields.map((item) => <li key={item}>{item}</li>)}</ul></details>}
            </article>
            {index < chain.nodes.length - 1 && <span className="vn-tax-chain-arrow">→</span>}
          </div>
        ))}
      </div>
      <div className="vn-tax-chain-assumption"><Info size={16} /><div><strong>当前口径</strong><span>{chain.assumptions.join(" ")}</span></div></div>
    </section>
  );
}

function PolicyGroups({ path, onReview }: { path: QuickEstimatePath; onReview: (policy: NonNullable<QuickEstimatePath["policy_matches"]>[number]) => void }) {
  const policies = path.policy_matches ?? [];
  const usable = policies.filter((item) => item.match_status.startsWith("AVAILABLE") || item.match_status.startsWith("APPLIED"));
  const pending = policies.filter((item) => item.match_status.includes("REQUIRED") || item.match_status.includes("ELIGIBILITY"));
  const notApplicable = policies.filter((item) => item.match_status.startsWith("NOT_APPLICABLE"));
  const group = (title: string, items: typeof policies, tone: string) => items.length > 0 && (
    <div className={`vn-policy-group ${tone}`}>
      <h4>{title}<small>{items.length}项</small></h4>
      {items.map((policy) => <article key={policy.program_code}><strong>{policy.program_name_cn}</strong><p>{policy.effect_on_calculation}</p><PolicyReviewTrigger onClick={() => onReview(policy)} /></article>)}
    </div>
  );
  return <div className="vn-policy-groups">
    {group("当前可直接进入候选", usable, "usable")}
    {group("满足条件后可使用", pending, "pending")}
    {group("当前不适用", notApplicable, "inactive")}
  </div>;
}

function VnCkdDutyResults({
  path,
  selectedCodes,
  onSelectCode,
  autoSelectionNotes,
}: {
  path: QuickEstimatePath;
  selectedCodes: Record<string, string>;
  onSelectCode: (ccuCode: string, code: string) => void;
  autoSelectionNotes: Record<string, string>;
}) {
  const lines = dutyLines(path);
  const topImpactLines = [...lines].sort((a, b) => Number(b.amount ?? 0) - Number(a.amount ?? 0)).slice(0, 4);
  return (
    <section className="ckd-results">
      <DecisionSummary path={path} />
      <FullTaxChain path={path} />
      <section className="ckd-section">
        <div className="ckd-section-header">
          <div>
            <span className="ckd-section-kicker">03 / CLASSIFICATION SCOPE</span>
            <h2>越南 CKD 归类方式</h2>
          </div>
          <p>当前按“主要部件分别归类”估算。若同批散件已具备整车基本特征，应进入海关预裁定，不应直接套零件税率。</p>
        </div>
        <div className="ckd-hs-banner">
          <div className="ckd-hs-code">
            <span>DECLARATION MODE</span>
            <strong>MULTI-HS</strong>
            <small>{path.candidate_tariffs[0]?.national_tariff_code ?? "MAJOR PARTS BOM"}</small>
          </div>
          <div className="ckd-hs-meta">
            <span className="ckd-pending-badge"><CircleAlert size={14} /> 候选税号待确认</span>
            <small>不按最低税率自动挑选；须按零件技术事实选择最终税号。</small>
          </div>
        </div>
      </section>

      <section className="ckd-section">
        <div className="ckd-section-header">
          <div>
            <span className="ckd-section-kicker">04 / IMPORT DUTY</span>
            <h2>主要部件进口关税估算</h2>
          </div>
          <p>这里展示已确认主要部件的进口关税；进口VAT、本地组装SCT/VAT在全链条视图中单独标出，不混入已知税额。</p>
        </div>
        <div className="ckd-duty-grid">
          <article className="ckd-duty-card mfn">
            <span className="ckd-duty-badge">MFN</span>
            <div className="ckd-duty-rate">{rateText(path.statutory.import_duty_rate)}</div>
            <div className="ckd-duty-detail">
              <span>普通主要零件关税</span>
              <code>{path.statutory.regime ?? "MFN 零件税率待补"}</code>
            </div>
            <div className="ckd-duty-eligibility"><Info size={14} />普通税率行尚未完整入库时，不输出虚假数字。</div>
          </article>
          <article className="ckd-duty-card acfta">
            <span className="ckd-duty-badge">FTA CANDIDATE</span>
            <div className="ckd-duty-rate">{rateText(path.incentive.import_duty_rate)}</div>
            <div className="ckd-duty-detail">
              <span>已选最终税号后的进口关税</span>
              <code>{path.incentive.regime ?? "FTA / ORIGIN 待确认"}</code>
            </div>
            <div className="ckd-duty-amount">税基{moneyText(path.incentive.base_value)}下关税：{moneyText(path.incentive.known_tax_amount)}</div>
          </article>
        </div>
        <div className="ckd-import-eff">
          <span>当前阶段有效输出</span>
          <div className="ckd-import-eff-list">
            <span className="ckd-eff-chip acfta">进口关税 {rateText(path.incentive.import_duty_rate)}</span>
            <span className="ckd-eff-chip mfn">完整综合税率：后续补充</span>
          </div>
        </div>
      </section>

      <section className="ckd-section">
        <div className="ckd-section-header">
          <div>
            <span className="ckd-section-kicker">05 / TARIFF SELECTION</span>
            <h2>确认主要部件最终税号</h2>
          </div>
          <p>候选已排除明确写作摩托车、拖拉机及商用车用途的税号；“其他”税号仍需按实际部件状态与越南海关口径确认。选完后再次点击上方“计算”刷新估算。</p>
        </div>
        <div className="vn-ckd-candidate-grid">
          {(path.component_candidates ?? []).map((component) => (
            <article className="vn-ckd-candidate-card" key={component.ccu_code}>
              <strong>{component.ccu_name_cn}</strong>
              <small>需要确认：{component.required_facts.map(factLabel).join("、") || "零件技术参数"}</small>
              <select
                value={selectedCodes[component.ccu_code] ?? ""}
                onChange={(event) => onSelectCode(component.ccu_code, event.target.value)}
              >
                <option value="">请选择最终税号（不会按最低税率强行选择）</option>
                {component.candidates.map((candidate) => (
                  <option key={`${candidate.agreement}-${candidate.national_tariff_code}`} value={candidate.national_tariff_code}>
                    {formatVietnameseCandidate(candidate)}
                  </option>
                ))}
              </select>
              {selectedCodes[component.ccu_code] && (
                <div className="vn-ckd-selected-note">
                  {autoSelectionNotes[component.ccu_code] ? `已自动带入：${autoSelectionNotes[component.ccu_code]}` : "已选择；如技术状态不同可手动更换"}
                </div>
              )}
              {!selectedCodes[component.ccu_code] && autoSelectionNotes[component.ccu_code] && component.candidates.length > 0 && (
                <div className="vn-ckd-selection-hint">{autoSelectionNotes[component.ccu_code]}</div>
              )}
              {component.candidates.length === 0 && <em>当前日期/原产国下没有可展示的候选税号，需补充官方税则数据。</em>}
            </article>
          ))}
        </div>
      </section>

      <section className="ckd-section">
        <div className="ckd-section-header">
          <div>
            <span className="ckd-section-kicker">06 / COMPONENT BREAKDOWN</span>
            <h2>主要部件关税拆分</h2>
          </div>
          <p>这里展示已确认税号后的税负贡献；没有最终税号时只显示“待确认”，不把候选税率当成确定结果。</p>
        </div>
        <div className="vn-ckd-component-table">
          {lines.length === 0 ? (
            <div className="ckd-missing-local"><CircleAlert size={18} /><div><strong>未找到可用税率行</strong>请确认原产国、FTA资格，或补充越南主要零件普通MFN税率。</div></div>
          ) : lines.map((line) => {
            const componentName = line.tax.replace("IMPORT_DUTY:", "");
            return (
              <article key={`${line.tax}-${line.formula}`}>
                <strong>{componentName}</strong>
                <span>{line.scope_note ?? "零件税号待确认"}</span>
                <em>{rateText(line.rate)}</em>
                <small>{moneyText(line.amount)} / 税基{moneyText(line.base)}</small>
              </article>
            );
          })}
        </div>
        {topImpactLines.length > 0 && (
          <div className="vn-impact-grid">
            {topImpactLines.map((line) => <article key={`impact-${line.tax}`}><span>{line.tax.replace("IMPORT_DUTY:", "")}</span><strong>{moneyText(line.amount)}</strong><small>税负贡献 / 标准化税基</small></article>)}
          </div>
        )}
        {path.missing_items.length > 0 && <div className="ckd-missing-local"><CircleAlert size={18} /><div><strong>补齐这些信息即可继续</strong>{path.missing_items.join("、")}</div></div>}
      </section>
    </section>
  );
}

export function VietnamCkdWorkspace({ embedded = false, onSnapshot }: ScenarioWorkspaceProps) {
  const [form, setForm] = useState({
    effective_date: new Date().toISOString().slice(0, 10),
    origin_country_iso2: "CN",
    powertrain: "BEV",
    engine_displacement_cc: "",
    engine_assembly: "COMPLETE" as "COMPLETE" | "PARTS" | "UNKNOWN",
    classification_mode: "PARTS_BOM",
    customs_value_ckd: "100",
  });
  const [result, setResult] = useState<QuickEstimateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCodes, setSelectedCodes] = useState<Record<string, string>>({});
  const [autoSelectionNotes, setAutoSelectionNotes] = useState<Record<string, string>>({});
  const [selectedPolicy, setSelectedPolicy] = useState<NonNullable<QuickEstimateResult["policy_matches"]>[number] | null>(null);

  const needsDisplacement = ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV"].includes(form.powertrain);

  // A changed scenario invalidates previously selected national tariff codes.
  // Keeping them would let a code from a different date/origin leak into the
  // next calculation.
  useEffect(() => {
    setSelectedCodes({});
    setAutoSelectionNotes({});
    setResult(null);
    onSnapshot?.(null);
  }, [form.effective_date, form.origin_country_iso2, form.powertrain, form.engine_displacement_cc, form.engine_assembly, form.classification_mode, form.customs_value_ckd, onSnapshot]);

  const components = useMemo(() => COMPONENTS_BY_POWERTRAIN[form.powertrain] ?? COMPONENTS_BY_POWERTRAIN.BEV, [form.powertrain]);
  const ckdPath = result?.paths.find((item) => item.path === "CKD");
  const matchedComponentNames = useMemo(() => new Set(
    (ckdPath?.component_candidates ?? [])
      .filter((item) => item.candidates.length > 0)
      .map((item) => item.ccu_name_cn),
  ), [ckdPath]);

  async function submit() {
    setError(null);
    setResult(null);
    if (form.classification_mode !== "PARTS_BOM") {
      setError("当前选择为整车归类风险场景，不能按零件税率估算。请先取得越南海关预裁定/归类意见，或切回“零件分别归类”。");
      return;
    }
    setLoading(true);
    try {
      const buildPayload = (codes: Record<string, string>) => ({
        country_iso2: "VN",
        origin_country_iso2: form.origin_country_iso2,
        effective_date: form.effective_date,
        path: "CKD" as const,
        powertrain: form.powertrain,
        cbu_tariff_code: null,
        ckd_tariff_code: null,
        ckd_declaration_mode: "PARTS_BOM" as const,
        customs_value_cbu: null,
        customs_value_ckd: form.customs_value_ckd || null,
        ckd_component_tariff_codes: codes,
      });
      const data = await createQuickEstimate(buildPayload(selectedCodes));
      const candidatePath = data.paths.find((item) => item.path === "CKD");
      const auto = candidateCodeMap(candidatePath, form.engine_displacement_cc, form.engine_assembly);
      const mergedCodes = { ...auto.codes, ...selectedCodes };
      const hasNewAutoSelections = Object.entries(auto.codes).some(([ccuCode, code]) => selectedCodes[ccuCode] !== code);
      setAutoSelectionNotes(auto.notes);
      let finalData = data;
      if (hasNewAutoSelections) {
        setSelectedCodes(mergedCodes);
        // Re-run once so the result shown immediately reflects the codes that
        // were safely determined from the supplied facts.
        const refreshed = await createQuickEstimate(buildPayload(mergedCodes));
        setResult(refreshed);
        finalData = refreshed;
      } else {
        setSelectedCodes(mergedCodes);
        setResult(data);
      }
      const finalPath = finalData.paths.find((item) => item.path === "CKD");
      if (finalPath) {
        const rates = [
          {
            regime: finalPath.statutory.regime ?? "MFN",
            rate: finalPath.statutory.effective_tax_rate ?? finalPath.statutory.import_duty_rate ?? null,
            scope: "IMPORT_STAGE" as const,
            complete: finalPath.statutory.import_duty_rate != null,
          },
          {
            regime: finalPath.incentive.regime ?? "优惠候选",
            rate: finalPath.incentive.effective_tax_rate ?? finalPath.incentive.import_duty_rate ?? null,
            scope: "IMPORT_STAGE" as const,
            complete: finalPath.incentive.import_duty_rate != null,
          },
        ].filter((item, index, items) => items.findIndex((candidate) => candidate.regime === item.regime && candidate.rate === item.rate) === index);
        onSnapshot?.({
          countryIso2: "VN",
          countryName: "越南",
          route: "CKD",
          title: "越南 CKD 主要部件进口",
          effectiveDate: form.effective_date,
          originCountryIso2: form.origin_country_iso2,
          powertrain: form.powertrain,
          status: rates.some((item) => item.rate != null) ? "PARTIAL" : "BLOCKED",
          confidence: finalPath.confidence,
          scopeLabel: "全链条视图：已知主要部件进口关税；本地SCT/VAT待补",
          tariffCodes: Object.values(mergedCodes).filter(Boolean),
          rates,
          missingItems: finalPath.missing_items,
          notes: ["当前只把已确认主要部件进口关税计入已知税额；进口VAT、本地组装SCT/VAT和终端销售VAT已在全链条视图中标记为待补。"],
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "越南 CKD 估算失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className={`ckd-page${embedded ? " scenario-workspace-embedded" : ""}`}>
      <div className="ckd-shell">
        <Link className="ckd-back" href="/decision/ckd"><ArrowLeft size={17} /> 返回 CKD 国家选择</Link>
        <header className="ckd-hero">
          <div>
            <span className="ckd-eyebrow"><PackageSearch size={14} /> VIETNAM CKD PARTS DUTY</span>
            <h1>越南 CKD 出口方案与全链条税负估算</h1>
            <p>按照越南 CKD 规划逻辑，先判断归类方式；当前以<strong>零件分别归类</strong>为主，已知进口关税与出口、组装、销售阶段的待补条件分开呈现。</p>
          </div>
          <span className="ckd-db-state"><Database size={17} /> 实时连接政策数据库</span>
        </header>

        <section className="ckd-input-card">
          <div className="ckd-input-grid">
            <label>
              <span><Factory size={15} /> 目标国家</span>
              <select value="VN" disabled><option value="VN">越南 · VN</option></select>
              <small>越南 CKD 专页，后续可继续接入本地SCT/VAT。</small>
            </label>
            <label>
              <span>原产国</span>
              <select value={form.origin_country_iso2} onChange={(event) => setForm((current) => ({ ...current, origin_country_iso2: event.target.value }))}>
                {ORIGINS.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
              </select>
              <small>决定 MFN / ACFTA / ATIGA / RCEP 等制度。</small>
            </label>
            <label>
              <span><CalendarDays size={15} /> 进口日期</span>
              <input type="date" value={form.effective_date} onChange={(event) => setForm((current) => ({ ...current, effective_date: event.target.value }))} />
              <small>匹配当期有效税率。</small>
            </label>
            <label>
              <span><Gauge size={15} /> 动力类型</span>
              <select value={form.powertrain} onChange={(event) => setForm((current) => ({ ...current, powertrain: event.target.value }))}>
                {POWERTRAINS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
              <small>决定纳入估算的主要部件组合。</small>
            </label>
            <label className={!needsDisplacement ? "is-disabled" : undefined}>
              <span>发动机排量（cc）</span>
              <input
                inputMode="numeric"
                type="number"
                min="1"
                step="1"
                value={needsDisplacement ? form.engine_displacement_cc : ""}
                disabled={!needsDisplacement}
                onChange={(event) => setForm((current) => ({ ...current, engine_displacement_cc: event.target.value }))}
                placeholder={needsDisplacement ? "例如 1498" : "BEV/FCEV不适用"}
              />
              <small>{needsDisplacement ? "用于自动匹配发动机排量档；完整发动机/零件状态仍可能需要确认。" : "纯电和氢燃料车辆不使用发动机排量条件。"}</small>
            </label>
            <label className={!needsDisplacement ? "is-disabled" : undefined}>
              <span>发动机进口状态</span>
              <select
                value={needsDisplacement ? form.engine_assembly : "UNKNOWN"}
                disabled={!needsDisplacement}
                onChange={(event) => setForm((current) => ({ ...current, engine_assembly: event.target.value as "COMPLETE" | "PARTS" | "UNKNOWN" }))}
              >
                <option value="COMPLETE">完整发动机总成（默认）</option>
                <option value="PARTS">发动机零件/未完整装配</option>
                <option value="UNKNOWN">尚未确认</option>
              </select>
              <small>{needsDisplacement ? "用于区分越南税则的 Fully assembled 与 Other 分支；实际状态不明时请选择“尚未确认”。" : "BEV/FCEV不适用。"}</small>
            </label>
            <label>
              <span>实际进口申报方式</span>
              <select value={form.classification_mode} onChange={(event) => setForm((current) => ({ ...current, classification_mode: event.target.value }))}>
                <option value="PARTS_BOM">零件分别归类（当前可估算）</option>
                <option value="GRI_2A_RISK">整车归类风险 / 需 Customs Ruling</option>
              </select>
              <small>若具备整车基本特征，需先走海关预裁定。</small>
            </label>
            <label>
              <span>标准化估算基数</span>
              <input inputMode="decimal" value={form.customs_value_ckd} onChange={(event) => setForm((current) => ({ ...current, customs_value_ckd: event.target.value }))} placeholder="默认100（非货币金额）" />
              <small>不填企业敏感BOM时使用；仅用于计算加权比例，不代表人民币、美元或单车CIF。</small>
            </label>
          </div>

          <details className="ckd-advanced" open>
            <summary><Info size={15} /> 当前动力类型主要部件（绿色＝已匹配候选；红色＝当前条件下没有候选）</summary>
            <div className="vn-ckd-component-tags">
              {components.map((item) => {
                const status = !ckdPath ? "pending" : (componentMatches(item, matchedComponentNames) ? "matched" : "missing");
                return <span className={`vn-ckd-component-tag ${status}`} key={item}>{item}</span>;
              })}
            </div>
          </details>

          {error && <div className="ckd-error"><ShieldAlert size={17} />{error}</div>}
          <button type="button" className="ckd-calculate-btn" disabled={loading} onClick={() => submit()}>
            {loading ? <><LoaderCircle className="spin" size={18} /> 计算中…</> : <><Calculator size={18} /> 生成越南 CKD 出口方案</>}
          </button>
        </section>

        {ckdPath ? <VnCkdDutyResults
          path={ckdPath}
          selectedCodes={selectedCodes}
          autoSelectionNotes={autoSelectionNotes}
          onSelectCode={(ccuCode, code) => {
            setSelectedCodes((current) => ({ ...current, [ccuCode]: code }));
            onSnapshot?.(null);
            setAutoSelectionNotes((current) => {
              const next = { ...current };
              delete next[ccuCode];
              return next;
            });
          }}
        /> : <div className="ckd-empty-hint"><Factory size={40} /><h3>输入 CKD 信息后点击计算</h3><p>系统会先列出与原产地和日期相符的部件候选税号；确认最终税号后才计算进口关税。</p></div>}

        {result?.policy_matches && result.policy_matches.length > 0 && (
          <section className="ckd-assumptions" style={{ marginTop: 32 }}>
            <header><span>POLICY OPPORTUNITIES</span><h3>政策机会与限制</h3><p>先显示可用机会，再折叠不适用政策，避免把“相关”误读为“已享受”。</p></header>
            <PolicyGroups path={ckdPath!} onReview={setSelectedPolicy} />
          </section>
        )}
        <PolicyReviewDrawer policy={selectedPolicy ? quickPolicyToReview(selectedPolicy) : null} onClose={() => setSelectedPolicy(null)} />
      </div>
    </main>
  );
}

export default function VietnamCkdPage() {
  return <VietnamCkdWorkspace />;
}
