"use client";

import {
  ArrowLeft,
  ArrowLeftRight,
  Columns2,
  Database,
  Focus,
  Info,
  RotateCcw,
  Scale,
  ShieldAlert,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import type { ScenarioRate, ScenarioSnapshot } from "../ScenarioWorkspace";
import { MalaysiaCbuWorkspace } from "../cbu/my/page";
import { VietnamCbuWorkspace } from "../cbu/vn/page";
import { MalaysiaCkdWorkspace } from "../ckd/my/page";
import { VietnamCkdWorkspace } from "../ckd/vn/page";

type CountryCode = "MY" | "VN";
type RouteCode = "CBU" | "CKD";
type Side = "A" | "B";
type FocusMode = "BOTH" | Side;
type WorkspaceConfig = { country: CountryCode; route: RouteCode };

const COUNTRIES: Array<{ value: CountryCode; label: string }> = [
  { value: "MY", label: "马来西亚 · MY" },
  { value: "VN", label: "越南 · VN" },
];

const ROUTES: Array<{ value: RouteCode; label: string; note: string }> = [
  { value: "CBU", label: "CBU 整车进口", note: "整车税号、进口关税及国内税链" },
  { value: "CKD", label: "CKD 散件组装", note: "整套税号或主要部件逐项归类" },
];

function percent(value: string | null | undefined) {
  if (value == null || value === "") return "待确认";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "待确认";
  return `${(parsed * 100).toFixed(2).replace(/\.00$/, "")}%`;
}

function statusLabel(value: ScenarioSnapshot["status"] | undefined) {
  if (value === "COMPLETE") return "完整可比";
  if (value === "PARTIAL") return "部分可算";
  if (value === "BLOCKED") return "暂不可算";
  return "等待计算";
}

function confidenceLabel(value: ScenarioSnapshot["confidence"] | undefined) {
  if (value === "HIGH") return "高";
  if (value === "MEDIUM") return "中";
  if (value === "LOW") return "低";
  return "—";
}

function preferredRate(snapshot: ScenarioSnapshot | null) {
  if (!snapshot) return null;
  return snapshot.rates.find((item) => item.complete && item.rate != null)
    ?? snapshot.rates.find((item) => item.rate != null)
    ?? null;
}

function findRate(snapshot: ScenarioSnapshot | null, regime: string) {
  return snapshot?.rates.find((item) => item.regime === regime && item.rate != null) ?? null;
}

function scopeText(rate: ScenarioRate) {
  if (rate.scope === "FULL_CHAIN") return "全税链";
  if (rate.scope === "IMPORT_STAGE") return "仅进口环节";
  return "部分税链";
}

function SummaryCard({ side, snapshot }: { side: Side; snapshot: ScenarioSnapshot | null }) {
  const rate = preferredRate(snapshot);
  return (
    <article className={`lab-summary-card side-${side.toLowerCase()} ${snapshot?.status.toLowerCase() ?? "empty"}`}>
      <div className="lab-summary-title"><span>方案 {side}</span><strong>{snapshot?.title ?? "尚未计算"}</strong></div>
      <div className="lab-summary-rate"><span>{snapshot?.scopeLabel ?? "等待专页结果"}</span><strong>{percent(rate?.rate)}</strong><small>{rate?.regime ?? "—"}</small></div>
      <dl>
        <div><dt>状态</dt><dd>{statusLabel(snapshot?.status)}</dd></div>
        <div><dt>可信度</dt><dd>{confidenceLabel(snapshot?.confidence)}</dd></div>
        <div><dt>税号</dt><dd>{snapshot?.tariffCodes.length ? `${snapshot.tariffCodes.length} 项` : "待确认"}</dd></div>
        <div><dt>缺失项</dt><dd>{snapshot?.missingItems.length ?? "—"}</dd></div>
      </dl>
    </article>
  );
}

function ComparisonResult({ left, right }: { left: ScenarioSnapshot | null; right: ScenarioSnapshot | null }) {
  const regimes = useMemo(() => Array.from(new Set([
    ...(left?.rates.map((item) => item.regime) ?? []),
    ...(right?.rates.map((item) => item.regime) ?? []),
  ])), [left, right]);
  const leftPreferred = preferredRate(left);
  const rightPreferred = preferredRate(right);
  const directlyComparable = Boolean(
    leftPreferred && rightPreferred
    && leftPreferred.scope === rightPreferred.scope
    && leftPreferred.rate != null && rightPreferred.rate != null,
  );
  const preferredDelta = directlyComparable
    ? (Number(leftPreferred!.rate) - Number(rightPreferred!.rate)) * 100
    : null;

  return (
    <section className="lab-summary" aria-live="polite">
      <header>
        <div><span>DECISION LAYER</span><h2>对比摘要</h2></div>
        <p>摘要只读取两套专页已经完成的计算，不在对比层重新猜税号或优惠资格。</p>
      </header>
      <div className="lab-summary-cards">
        <SummaryCard side="A" snapshot={left} />
        <div className="lab-summary-delta">
          <Scale size={18} />
          {preferredDelta == null ? (
            <><strong>暂不输出差额</strong><small>{left && right ? "两侧税负范围不同或仍缺数字" : "请分别完成方案 A 和 B"}</small></>
          ) : (
            <><strong>{Math.abs(preferredDelta).toFixed(2)} pp</strong><small>{preferredDelta > 0 ? "方案 B 税率较低" : preferredDelta < 0 ? "方案 A 税率较低" : "两侧相同"}</small></>
          )}
        </div>
        <SummaryCard side="B" snapshot={right} />
      </div>
      {left && right && regimes.length > 0 && (
        <div className="lab-regime-table">
          <div className="lab-regime-row head"><span>制度 / 情景</span><span>方案 A</span><span>差额</span><span>方案 B</span></div>
          {regimes.map((regime) => {
            const a = findRate(left, regime);
            const b = findRate(right, regime);
            const comparable = Boolean(a && b && a.scope === b.scope);
            const delta = comparable ? (Number(a!.rate) - Number(b!.rate)) * 100 : null;
            return (
              <div className="lab-regime-row" key={regime}>
                <strong>{regime}</strong>
                <span>{percent(a?.rate)}<small>{a ? scopeText(a) : "无匹配结果"}</small></span>
                <em>{delta == null ? "不可直接相减" : `${Math.abs(delta).toFixed(2)} pp`}</em>
                <span>{percent(b?.rate)}<small>{b ? scopeText(b) : "无匹配结果"}</small></span>
              </div>
            );
          })}
        </div>
      )}
      {left && right && !directlyComparable && (
        <div className="lab-scope-warning"><Info size={16} /><span>两侧当前不是同一计算范围。系统保留各自结果供决策参考，但不会把“进口环节税率”和“全流程综合税率”强行相减。</span></div>
      )}
    </section>
  );
}

function Workspace({ config, onSnapshot }: { config: WorkspaceConfig; onSnapshot: (value: ScenarioSnapshot | null) => void }) {
  if (config.country === "MY" && config.route === "CBU") return <MalaysiaCbuWorkspace embedded onSnapshot={onSnapshot} />;
  if (config.country === "MY" && config.route === "CKD") return <MalaysiaCkdWorkspace embedded onSnapshot={onSnapshot} />;
  if (config.country === "VN" && config.route === "CBU") return <VietnamCbuWorkspace embedded onSnapshot={onSnapshot} />;
  return <VietnamCkdWorkspace embedded onSnapshot={onSnapshot} />;
}

function WorkspacePanel({ side, config, snapshot, onConfig, onSnapshot, onFocus }: {
  side: Side;
  config: WorkspaceConfig;
  snapshot: ScenarioSnapshot | null;
  onConfig: (value: WorkspaceConfig) => void;
  onSnapshot: (value: ScenarioSnapshot | null) => void;
  onFocus: () => void;
}) {
  const route = ROUTES.find((item) => item.value === config.route)!;
  return (
    <section className={`lab-workspace side-${side.toLowerCase()}`}>
      <header className="lab-workspace-header">
        <div className="lab-side-badge">{side}</div>
        <div className="lab-workspace-selectors">
          <label><span>目标国家</span><select value={config.country} onChange={(event) => onConfig({ ...config, country: event.target.value as CountryCode })}>{COUNTRIES.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
          <label><span>进口路径</span><select value={config.route} onChange={(event) => onConfig({ ...config, route: event.target.value as RouteCode })}>{ROUTES.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
        </div>
        <div className="lab-workspace-state"><span className={snapshot?.status.toLowerCase() ?? "empty"}>{statusLabel(snapshot?.status)}</span><small>{route.note}</small></div>
        <button type="button" className="lab-focus-button" onClick={onFocus} title={`聚焦方案 ${side}`}><Focus size={16} /></button>
      </header>
      <div className="lab-workspace-body" key={`${side}-${config.country}-${config.route}`}><Workspace config={config} onSnapshot={onSnapshot} /></div>
    </section>
  );
}

export default function ComparePage() {
  const [leftConfig, setLeftConfig] = useState<WorkspaceConfig>({ country: "MY", route: "CBU" });
  const [rightConfig, setRightConfig] = useState<WorkspaceConfig>({ country: "MY", route: "CKD" });
  const [leftSnapshot, setLeftSnapshot] = useState<ScenarioSnapshot | null>(null);
  const [rightSnapshot, setRightSnapshot] = useState<ScenarioSnapshot | null>(null);
  const [focus, setFocus] = useState<FocusMode>("BOTH");
  const handleLeftSnapshot = useCallback((value: ScenarioSnapshot | null) => setLeftSnapshot(value), []);
  const handleRightSnapshot = useCallback((value: ScenarioSnapshot | null) => setRightSnapshot(value), []);

  function changeLeft(value: WorkspaceConfig) { setLeftConfig(value); setLeftSnapshot(null); }
  function changeRight(value: WorkspaceConfig) { setRightConfig(value); setRightSnapshot(null); }
  function swap() {
    setLeftConfig(rightConfig); setRightConfig(leftConfig);
    setLeftSnapshot(rightSnapshot); setRightSnapshot(leftSnapshot);
  }
  function reset() {
    setLeftConfig({ country: "MY", route: "CBU" });
    setRightConfig({ country: "MY", route: "CKD" });
    setLeftSnapshot(null); setRightSnapshot(null); setFocus("BOTH");
  }

  return (
    <main className="lab-page">
      <div className="lab-shell">
        <Link className="lab-back" href="/"><ArrowLeft size={17} /> 返回全球决策</Link>
        <header className="lab-hero">
          <div><span><ArrowLeftRight size={14} /> FULL-GRANULARITY COMPARISON</span><h1>方案对比实验室</h1><p>在同一页面运行两套完整决策工具。国家、CBU/CKD 路径、车辆条件、税号和优惠资格均可独立配置。</p></div>
          <div className="lab-db-state"><Database size={17} /> 实时读取政策数据库</div>
        </header>
        <div className="lab-toolbar">
          <div className="lab-view-switch" role="group" aria-label="工作区布局">
            <button className={focus === "BOTH" ? "active" : ""} onClick={() => setFocus("BOTH")} type="button"><Columns2 size={15} /> 并排</button>
            <button className={focus === "A" ? "active" : ""} onClick={() => setFocus("A")} type="button"><Focus size={15} /> 聚焦 A</button>
            <button className={focus === "B" ? "active" : ""} onClick={() => setFocus("B")} type="button"><Focus size={15} /> 聚焦 B</button>
          </div>
          <div className="lab-toolbar-actions"><button type="button" onClick={swap}><ArrowLeftRight size={15} /> 交换方案</button><button type="button" onClick={reset}><RotateCcw size={15} /> 重置</button></div>
        </div>
        <ComparisonResult left={leftSnapshot} right={rightSnapshot} />
        <div className={`lab-workspaces focus-${focus.toLowerCase()}`}>
          {(focus === "BOTH" || focus === "A") && <WorkspacePanel side="A" config={leftConfig} snapshot={leftSnapshot} onConfig={changeLeft} onSnapshot={handleLeftSnapshot} onFocus={() => setFocus("A")} />}
          {(focus === "BOTH" || focus === "B") && <WorkspacePanel side="B" config={rightConfig} snapshot={rightSnapshot} onConfig={changeRight} onSnapshot={handleRightSnapshot} onFocus={() => setFocus("B")} />}
        </div>
        <div className="lab-method-note"><ShieldAlert size={16} /><span>只有两侧采用相同税负范围时，系统才计算百分点差额。所有税号、政策条件与缺失项仍以各自专页结果为准。</span></div>
      </div>
    </main>
  );
}
