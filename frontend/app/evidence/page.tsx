"use client";

import {
  ArrowLeft, BookOpen, Calculator, CheckCircle2, ChevronDown, ChevronRight,
  Database, ExternalLink, FileText, Info, LoaderCircle, Search, ShieldCheck, X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  type EvidenceItem,
  type PolicyRule,
  type PolicyRulesResponse,
  type SourceEvidenceDetail,
  filterPolicyRules,
  getCountryRules,
  getSourceEvidence,
} from "../lib/api";

// ── Constants ──
const DOMAINS = [
  "IMPORT_DUTY", "EXCISE", "SALES_TAX", "VAT_GST", "FTA",
  "INCENTIVE", "LOCALIZATION", "VALUATION", "APPROVAL",
];
const STATUSES = ["VERIFIED", "CANDIDATE", "UNVERIFIED"];

const SOURCE_TYPE_CN: Record<string, string> = {
  GAZETTE: "法规", TARIFF_SCHEDULE: "税则", REGULATION: "条例",
  TREATY: "条约", OFFICIAL_GUIDE: "官方指南", OFFICIAL_PORTAL: "官方查询",
  BUDGET_DOCUMENT: "预算文件", LAW: "法律",
};
const EVIDENCE_ROLE_CN: Record<string, string> = {
  TARIFF_RATE: "税率依据", TAX_FORMULA: "计算规则", ELIGIBILITY: "资格依据",
  ORIGIN_RULE: "原产地规则", INCENTIVE: "优惠政策", CLASSIFICATION: "归类依据",
};

function fmtDate(d: string | null): string {
  if (!d) return "至今";
  return d.slice(0, 10);
}

function Badge({ label, clr = "neutral" }: { label: string; clr?: string }) {
  return <span className={`ev-badge ev-badge-${clr}`}>{label}</span>;
}

// ── Source Detail Drawer ───────────────────────────────────────────

function SourceDrawer({ item, onClose }: { item: EvidenceItem; onClose: () => void }) {
  const [detail, setDetail] = useState<SourceEvidenceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true); setError(null);
    getSourceEvidence(item.document_id)
      .then(setDetail).catch((e) => setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [item.document_id]);

  return (
    <div className="ev-drawer-overlay" onClick={onClose}>
      <div className="ev-drawer" onClick={(e) => e.stopPropagation()}>
        <header className="ev-drawer-head">
          <div>
            <span className="ev-drawer-kicker">官方依据</span>
            <h3>{item.document_title}</h3>
          </div>
          <button type="button" className="ev-drawer-close" onClick={onClose}><X size={18} /></button>
        </header>
        <div className="ev-drawer-body">
          <div className="ev-drawer-meta">
            <span><strong>角色:</strong> {EVIDENCE_ROLE_CN[item.evidence_role] || item.evidence_role}</span>
            <span><strong>类型:</strong> {SOURCE_TYPE_CN[item.source_type] || item.source_type}</span>
            <span><strong>主管机关:</strong> {item.authority_name}</span>
            <span><strong>定位:</strong> {item.locator_value}</span>
          </div>

          {loading && <div className="ev-drawer-loading"><LoaderCircle className="spin" size={18} /> 加载原文…</div>}
          {error && <div className="ev-drawer-error">{error}</div>}

          {detail && (
            <>
              {detail.original_excerpt && (
                <div className="ev-drawer-excerpt">
                  <span>原文摘录</span>
                  <p>{detail.original_excerpt}</p>
                </div>
              )}
              {detail.translated_excerpt_cn && (
                <div className="ev-drawer-excerpt">
                  <span>中文译文</span>
                  <p>{detail.translated_excerpt_cn}</p>
                </div>
              )}
            </>
          )}

          <div className="ev-drawer-actions">
            <span className="ev-drawer-summary">{item.evidence_summary}</span>
            {item.official_url && (
              <a href={item.official_url} target="_blank" rel="noopener noreferrer" className="ev-drawer-external">
                <ExternalLink size={14} /> 查看官方文件 ↗
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Detail Panel ────────────────────────────────────────────────────

function DetailPanel({ rule }: { rule: PolicyRule }) {
  const [drawerItem, setDrawerItem] = useState<EvidenceItem | null>(null);
  const [showCalc, setShowCalc] = useState(false);
  const [showTech, setShowTech] = useState(false);

  const modes = rule.impact_scope?.vehicle_modes?.map((m) => m === "CBU" ? "CBU（整车进口）" : m === "CKD" ? "CKD（本地组装）" : m).join(" · ") || "未知";
  const pts = rule.impact_scope?.powertrains?.join(" · ") || (rule.impact_scope?.powertrains === null ? "未知" : "不限");
  const taxes = rule.impact_scope?.taxes?.join(" · ") || (rule.impact_scope?.taxes === null ? "未知" : "—");

  return (
    <div className="ev-detail">
      {/* ① Overview + Impact */}
      <section className="ev-detail-sec">
        <div className="ev-detail-topline">
          <Badge label={rule.rule_domain} clr="domain" />
          <span className={`ev-status-dot ${rule.verification_status === "VERIFIED" ? "verified" : "candidate"}`}>
            {rule.verification_status === "VERIFIED" ? "● 已核验" : "○ 待确认"}
          </span>
        </div>
        <h2>{rule.rule_name_cn}</h2>
        <p className="ev-detail-desc">{rule.rule_content}</p>
        <div className="ev-detail-version">
          版本: {rule.tariff_version || "—"} · {fmtDate(rule.effective_from)} ~ {fmtDate(rule.effective_to)}
        </div>

        <div className="ev-impact">
          <span className="ev-impact-title">影响范围</span>
          <div className="ev-impact-tags">
            <span className="ev-impact-tag">模式: {modes}</span>
            <span className="ev-impact-tag">动力: {pts}</span>
            <span className="ev-impact-tag">税种: {taxes}</span>
          </div>
        </div>
      </section>

      {/* ② Evidence */}
      <section className="ev-detail-sec">
        <h3 className="ev-sec-title"><FileText size={15} /> 官方依据</h3>
        <div className="ev-evidence-list">
          {rule.evidence.map((ev, i) => (
            <div key={i} className="ev-evidence-item"
                 onClick={() => setDrawerItem(ev)}>
              <span className="ev-evidence-role">{EVIDENCE_ROLE_CN[ev.evidence_role] || ev.evidence_role}</span>
              <div className="ev-evidence-info">
                <strong>{ev.document_title}</strong>
                <small>{ev.authority_name} · {ev.locator_value}</small>
              </div>
              <ChevronRight size={15} />
            </div>
          ))}
        </div>
      </section>

      {/* ③ Conditions */}
      <section className="ev-detail-sec">
        <h3 className="ev-sec-title"><ShieldCheck size={15} /> 适用条件</h3>
        {rule.condition_summary_status === "FALLBACK" && (
          <span className="ev-fallback-warn">⚠ 自动推断</span>
        )}
        <div className="ev-condition-tags">
          {rule.condition_summary.map((c, i) => (
            <span key={i} className="ev-condition-tag">✓ {c}</span>
          ))}
        </div>
      </section>

      {/* ④ Calculation Logic */}
      <section className="ev-detail-sec collapsible">
        <button type="button" className="ev-collapse-btn" onClick={() => setShowCalc(!showCalc)}>
          <Calculator size={15} />
          计算逻辑
          {rule.formula_summary_status === "FALLBACK" && <span className="ev-fallback-warn">⚠</span>}
          <ChevronDown className={showCalc ? "rotated" : ""} size={15} />
        </button>
        {showCalc && (
          <div className="ev-collapse-body">
            {rule.formula_summary.map((f, i) => (
              <div key={i} className="ev-formula-line">{f}</div>
            ))}
          </div>
        )}
      </section>

      {/* ⑤ Technical Info */}
      <section className="ev-detail-sec collapsible">
        <button type="button" className="ev-collapse-btn" onClick={() => setShowTech(!showTech)}>
          <Info size={15} />
          技术信息
          <ChevronDown className={showTech ? "rotated" : ""} size={15} />
        </button>
        {showTech && (
          <div className="ev-collapse-body ev-tech-body">
            <div><span>规则代码:</span> <code>{rule.rule_code}</code></div>
            <div><span>条款代码:</span> <code>{rule.clause_code}</code></div>
            {rule.verified_at && <div><span>核验时间:</span> {fmtDate(rule.verified_at)}</div>}
            {rule.verified_by && <div><span>核验人:</span> {rule.verified_by}</div>}
          </div>
        )}
      </section>

      {drawerItem && <SourceDrawer item={drawerItem} onClose={() => setDrawerItem(null)} />}
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────────

export default function EvidencePage() {
  const [data, setData] = useState<PolicyRulesResponse | null>(null);
  const [selected, setSelected] = useState<PolicyRule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [fDomain, setFDomain] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fQ, setFQ] = useState("");

  useEffect(() => {
    setLoading(true); setError(null);
    getCountryRules("MY")
      .then((d) => { setData(d); setSelected(d.items[0] || null); })
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    return filterPolicyRules(data.items, { domain: fDomain || undefined, status: fStatus || undefined, q: fQ || undefined });
  }, [data, fDomain, fStatus, fQ]);

  return (
    <main className="ev-page">
      <div className="ev-shell">
        <Link className="ev-back" href="/"><ArrowLeft size={17} /> 返回全球决策</Link>

        <header className="ev-hero">
          <div>
            <span className="ev-eyebrow"><BookOpen size={14} /> POLICY INTELLIGENCE</span>
            <h1>全球汽车政策库</h1>
            <p>
              马来西亚 · {data?.total ?? "—"} 条规则 · 9 个政策领域 · 264 份官方文件
              {data?.total && data.total > 0 && ` · 最近核验: ${data.items[0]?.verified_at ? fmtDate(data.items[0].verified_at) : "—"}`}
            </p>
          </div>
          <span className="ev-db-state"><Database size={17} /> 实时连接政策数据库</span>
        </header>

        {loading && (
          <div className="ev-loading"><LoaderCircle className="spin" size={24} /> 正在加载政策数据…</div>
        )}
        {error && <div className="ev-error">{error}</div>}

        {data && (
          <div className="ev-two-col">
            {/* Left 45% */}
            <section className="ev-list-col">
              <div className="ev-filter-bar">
                <div className="ev-filter-row">
                  <select value={fDomain} onChange={(e) => setFDomain(e.target.value)}>
                    <option value="">全部领域</option>
                    {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                  <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
                    <option value="">全部状态</option>
                    {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="ev-search-wrap">
                  <Search size={14} />
                  <input type="text" value={fQ} onChange={(e) => setFQ(e.target.value)}
                         placeholder="搜索规则/来源…" />
                </div>
                <small className="ev-filter-count">共 {filtered.length} 条</small>
              </div>

              <div className="ev-list">
                {filtered.map((rule) => (
                  <button
                    key={rule.rule_code}
                    type="button"
                    className={`ev-list-item ${selected?.rule_code === rule.rule_code ? "active" : ""}`}
                    onClick={() => setSelected(rule)}
                  >
                    <div className="ev-list-top">
                      <span className={`ev-status-dot ${rule.verification_status === "VERIFIED" ? "verified" : "candidate"}`}>
                        {rule.verification_status === "VERIFIED" ? "●" : "○"}
                      </span>
                      <strong className="ev-list-name">{rule.rule_name_cn}</strong>
                    </div>
                    <div className="ev-list-meta">
                      <Badge label={rule.rule_domain} clr="domain" />
                      {rule.impact_scope?.vehicle_modes?.map((m) => (
                        <span key={m} className="ev-list-mode">{m}</span>
                      ))}
                      {rule.impact_scope?.taxes?.map((t) => (
                        <span key={t} className="ev-list-tax">{t}</span>
                      ))}
                    </div>
                    <div className="ev-list-sub">
                      <span>{rule.tariff_version}</span>
                      <span>·</span>
                      <span>{fmtDate(rule.effective_from)}</span>
                    </div>
                    <div className="ev-list-sources">
                      {rule.evidence.slice(0, 3).map((ev, i) => (
                        <span key={i} className="ev-list-src-tag">{EVIDENCE_ROLE_CN[ev.evidence_role] || ev.evidence_role}</span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </section>

            {/* Right 55% */}
            <section className="ev-detail-col">
              {selected ? (
                <DetailPanel rule={selected} />
              ) : (
                <div className="ev-empty-detail">
                  <BookOpen size={36} />
                  <h3>选择左侧政策规则</h3>
                  <p>查看规则详情、影响范围、官方依据和计算逻辑</p>
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </main>
  );
}
