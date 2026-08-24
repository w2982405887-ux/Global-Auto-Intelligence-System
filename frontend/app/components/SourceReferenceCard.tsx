"use client";

import { ExternalLink, FileText, Info } from "lucide-react";
import { useState } from "react";
import { type SourceEvidenceDetail, getSourceEvidence } from "../lib/api";

// Minimal source-reference payload embedded in tariff/domestic-tax responses
export type EmbeddedSourceRef = {
  source_id?: string;
  document_title?: string;
  authority_name?: string;
  document_number?: string | null;
  source_type?: string;
  official_url?: string | null;
  locator?: { locator_type?: string; locator_value?: string };
};

type Props = {
  ruleRef?: { rule_id?: string | null; rule_type?: string | null; rule_description?: string | null };
  sourceRef?: EmbeddedSourceRef | null;
};

export default function SourceReferenceCard({ ruleRef, sourceRef }: Props) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<SourceEvidenceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sourceId = sourceRef?.source_id;
  const hasInfo = Boolean(ruleRef?.rule_id || sourceId);

  if (!hasInfo) return null;

  async function loadDetail() {
    if (!sourceId) return;
    setLoading(true);
    setError(null);
    try {
      setDetail(await getSourceEvidence(sourceId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="src-ref-card">
      <button
        type="button"
        className="src-ref-toggle"
        onClick={() => {
          if (!open && !detail) loadDetail();
          setOpen(!open);
        }}
        title="查看政策依据"
      >
        <FileText size={13} />
        来源
      </button>

      {open && (
        <div className="src-ref-panel">
          {/* Rule reference */}
          {ruleRef?.rule_id && (
            <div className="src-ref-line">
              <span>规则 ID</span>
              <code>{ruleRef.rule_type ?? "—"} · {ruleRef.rule_id?.slice(0, 8)}…</code>
            </div>
          )}

          {/* Source reference */}
          {sourceRef?.document_title && (
            <div className="src-ref-line">
              <span>官方文件</span>
              <strong>{sourceRef.document_title}</strong>
            </div>
          )}
          {sourceRef?.authority_name && (
            <div className="src-ref-line">
              <span>主管机关</span>
              <span>{sourceRef.authority_name}</span>
            </div>
          )}
          {sourceRef?.locator?.locator_value && (
            <div className="src-ref-line">
              <span>定位</span>
              <span>{sourceRef.locator.locator_value}</span>
            </div>
          )}

          {/* Detail */}
          {loading && <div className="src-ref-loading">加载中…</div>}
          {error && <div className="src-ref-error">{error}</div>}
          {detail && (
            <>
              {detail.original_excerpt && (
                <div className="src-ref-excerpt">
                  <span>原文摘录</span>
                  <p>{detail.original_excerpt.slice(0, 300)}{detail.original_excerpt.length > 300 ? "…" : ""}</p>
                </div>
              )}
              {detail.translated_excerpt_cn && (
                <div className="src-ref-excerpt">
                  <span>中文译文</span>
                  <p>{detail.translated_excerpt_cn.slice(0, 300)}{detail.translated_excerpt_cn.length > 300 ? "…" : ""}</p>
                </div>
              )}
              {detail.official_url && (
                <a
                  className="src-ref-url"
                  href={detail.official_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink size={13} />
                  查看官方文件 ↗
                </a>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
