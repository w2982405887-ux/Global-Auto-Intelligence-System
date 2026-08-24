"use client";

import { ExternalLink, FileText, LoaderCircle, X } from "lucide-react";
import { useEffect, useState } from "react";
import {
  getSourceEvidence,
  type QuickPolicyMatch,
  type RecentPolicy,
  type ResolvedPolicyView,
  type SourceEvidenceDetail,
  type SourceReferenceFields,
} from "../lib/api";

export type PolicyReviewRecord = {
  code: string;
  name: string;
  description?: string | null;
  status?: string | null;
  domain?: string | null;
  scope?: string | null;
  effectiveFrom?: string | null;
  effectiveTo?: string | null;
  reason?: string | null;
  conditions?: string[];
  requiredDocuments?: string[];
  conditionExpression?: Record<string, unknown> | null;
  benefitExpression?: Record<string, unknown> | null;
  sourceReference?: SourceReferenceFields | null;
};

export function recentPolicyToReview(policy: RecentPolicy): PolicyReviewRecord {
  return {
    code: policy.rule_code,
    name: policy.rule_name_cn,
    description: policy.rule_content,
    status: policy.verification_status,
    domain: policy.rule_domain,
    effectiveFrom: policy.effective_from,
    effectiveTo: policy.effective_to,
    conditionExpression: policy.condition_expression,
    benefitExpression: policy.benefit_expression,
    sourceReference: policy.source_reference ?? {
      source_id: policy.source_code,
      document_title: policy.document_title,
      document_number: policy.document_number,
      source_type: policy.source_type ?? undefined,
      authority_name: policy.authority_name ?? undefined,
      official_url: policy.canonical_url,
      locator: { locator_type: policy.locator_type ?? undefined, locator_value: policy.source_locator },
    },
  };
}

export function quickPolicyToReview(policy: QuickPolicyMatch): PolicyReviewRecord {
  return {
    code: policy.program_code,
    name: policy.program_name_cn,
    description: policy.description ?? policy.effect_on_calculation,
    status: policy.match_status,
    scope: policy.incentive_scope,
    effectiveFrom: policy.effective_from,
    effectiveTo: policy.effective_to,
    reason: policy.reason,
    conditionExpression: policy.condition_expression,
    benefitExpression: policy.benefit_expression,
    sourceReference: policy.source_reference,
  };
}

export function resolvedPolicyToReview(policy: ResolvedPolicyView): PolicyReviewRecord {
  return {
    code: policy.program_code,
    name: policy.program_name_cn,
    description: policy.incentive_scope,
    status: policy.status,
    effectiveFrom: policy.effective_from,
    effectiveTo: policy.effective_to,
    conditions: policy.matched_conditions,
    requiredDocuments: policy.required_documents,
    conditionExpression: policy.condition_expression,
    benefitExpression: policy.benefit_expression ?? policy.benefit?.overrides,
    sourceReference: policy.source_reference,
  };
}

function jsonText(value: unknown) {
  if (!value || typeof value !== "object" || Object.keys(value as object).length === 0) return null;
  return JSON.stringify(value, null, 2);
}

export function PolicyReviewDrawer({ policy, onClose }: { policy: PolicyReviewRecord | null; onClose: () => void }) {
  const [evidence, setEvidence] = useState<SourceEvidenceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEvidence(null);
    setError(null);
    const sourceId = policy?.sourceReference?.source_id;
    if (!policy || !sourceId) return;
    let cancelled = false;
    setLoading(true);
    getSourceEvidence(sourceId).then((data) => {
      if (!cancelled) setEvidence(data);
    }).catch((cause) => {
      if (!cancelled) setError(cause instanceof Error ? cause.message : "来源证据读取失败");
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [policy]);

  if (!policy) return null;
  const source = policy.sourceReference;
  const original = evidence?.original_excerpt ?? source?.original_excerpt;
  const translated = evidence?.translated_excerpt_cn ?? source?.translated_excerpt_cn;
  return (
    <div className="ev-drawer-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <aside className="ev-drawer" role="dialog" aria-modal="true" aria-label="政策说明与出处">
        <div className="ev-drawer-head">
          <div><span className="ev-drawer-kicker">POLICY REVIEW · 可追溯审核</span><h3>{policy.name}</h3></div>
          <button type="button" className="ev-drawer-close" onClick={onClose} aria-label="关闭"><X size={18} /></button>
        </div>
        <div className="ev-drawer-body">
          <div className="ev-drawer-meta">
            <div><strong>规则代码</strong><code>{policy.code}</code></div>
            {policy.status && <div><strong>当前状态</strong>{policy.status}</div>}
            {policy.domain && <div><strong>规则领域</strong>{policy.domain}</div>}
            {policy.scope && <div><strong>影响范围</strong>{policy.scope}</div>}
            {(policy.effectiveFrom || policy.effectiveTo) && <div><strong>有效期</strong>{policy.effectiveFrom ?? "—"} 至 {policy.effectiveTo ?? "持续"}</div>}
          </div>
          <section className="ev-drawer-excerpt"><span>政策描述</span><p>{policy.description || "数据库尚未提供规则正文，请以来源文件为准。"}</p></section>
          {policy.reason && <section className="ev-drawer-excerpt"><span>本次匹配说明</span><p>{policy.reason}</p></section>}
          {policy.conditions && policy.conditions.length > 0 && <section className="ev-drawer-excerpt"><span>已识别条件</span><p>{policy.conditions.join("；")}</p></section>}
          {policy.requiredDocuments && policy.requiredDocuments.length > 0 && <section className="ev-drawer-excerpt"><span>需要确认的材料</span><p>{policy.requiredDocuments.join("；")}</p></section>}
          {loading && <div className="ev-drawer-loading"><LoaderCircle className="spin" size={15} />正在读取来源摘录…</div>}
          {error && <div className="ev-drawer-error">{error}</div>}
          {original && <section className="ev-drawer-excerpt"><span>官方原文摘录</span><p>{original}</p></section>}
          {translated && <section className="ev-drawer-excerpt"><span>中文译文摘录</span><p>{translated}</p></section>}
          {jsonText(policy.conditionExpression) && <section className="ev-drawer-excerpt"><span>适用条件（结构化）</span><pre>{jsonText(policy.conditionExpression)}</pre></section>}
          {jsonText(policy.benefitExpression) && <section className="ev-drawer-excerpt"><span>政策效果（结构化）</span><pre>{jsonText(policy.benefitExpression)}</pre></section>}
          <div className="ev-drawer-actions">
            <span className="ev-drawer-summary"><FileText size={14} /> {source?.document_title || "来源文件信息待补录"}{source?.authority_name ? ` · ${source.authority_name}` : ""}{source?.locator?.locator_value ? ` · ${source.locator.locator_value}` : ""}</span>
            {(evidence?.official_url ?? source?.official_url) && <a className="ev-drawer-external" href={evidence?.official_url ?? source?.official_url ?? "#"} target="_blank" rel="noopener noreferrer">查看官方文件 <ExternalLink size={13} /></a>}
          </div>
        </div>
      </aside>
    </div>
  );
}

export function PolicyReviewTrigger({ onClick }: { onClick: () => void }) {
  return <button type="button" className="policy-review-trigger" onClick={onClick}><FileText size={13} />查看说明与出处</button>;
}
