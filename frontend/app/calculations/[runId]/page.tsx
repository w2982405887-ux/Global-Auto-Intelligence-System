"use client";

import {
  ArrowLeft,
  CircleAlert,
  Database,
  FileCheck2,
  GitBranch,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  type CalculationMissingItem,
  type CalculationRunDetail,
  type DecisionTraceItem,
  getCalculationMissingData,
  getCalculationRun,
  getCalculationTrace,
} from "../../lib/api";

export default function CalculationResultPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const [detail, setDetail] = useState<CalculationRunDetail | null>(null);
  const [trace, setTrace] = useState<DecisionTraceItem[]>([]);
  const [missing, setMissing] = useState<CalculationMissingItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    Promise.all([
      getCalculationRun(runId),
      getCalculationTrace(runId),
      getCalculationMissingData(runId),
    ])
      .then(([nextDetail, nextTrace, nextMissing]) => {
        setDetail(nextDetail);
        setTrace(nextTrace.items);
        setMissing(nextMissing.items);
      })
      .catch((cause) =>
        setError(cause instanceof Error ? cause.message : "计算结果读取失败"),
      );
  }, [runId]);

  if (error) {
    return (
      <main className="calculation-result-shell">
        <div className="decision-message error">
          <CircleAlert size={16} />
          {error}
        </div>
      </main>
    );
  }
  if (!detail) {
    return (
      <main className="calculation-result-shell loading">
        <LoaderCircle className="spin" size={26} />
        正在读取不可变计算快照
      </main>
    );
  }

  const run = detail.run;
  return (
    <main className="calculation-result-shell">
      <header className="calculation-result-header">
        <a href="/decision/new">
          <ArrowLeft size={15} />
          返回决策向导
        </a>
        <div>
          <span>DETERMINISTIC CALCULATION RUN</span>
          <h1>{run.project_name}</h1>
          <p>
            {run.run_code} · {run.route_name_cn}
          </p>
        </div>
        <div className={`run-status ${run.completeness.toLowerCase()}`}>
          <Database size={15} />
          {run.completeness}
        </div>
      </header>

      <section className="run-kpi-grid">
        <article>
          <span>海关价值</span>
          <strong>MYR {run.base_value}</strong>
        </article>
        <article>
          <span>综合税额</span>
          <strong>MYR {run.gross_tax}</strong>
        </article>
        <article>
          <span>净税额</span>
          <strong>MYR {run.net_tax}</strong>
        </article>
        <article>
          <span>综合税率</span>
          <strong>{(Number(run.effective_tax_rate) * 100).toFixed(2)}%</strong>
        </article>
      </section>

      <section className="result-panel">
        <div className="result-panel-heading">
          <FileCheck2 size={18} />
          <div>
            <span>CALCULATION LINE</span>
            <h2>逐项计算过程</h2>
          </div>
        </div>
        <div className="result-table">
          <div className="result-table-row header">
            <span>顺序/税种</span>
            <span>税基</span>
            <span>税率</span>
            <span>税额</span>
            <span>公式</span>
          </div>
          {detail.lines.map((line) => (
            <div className="result-table-row" key={line.sequence_no}>
              <strong>
                {line.sequence_no}. {line.tax_code}
              </strong>
              <span>MYR {line.base_amount}</span>
              <span>{(Number(line.rate) * 100).toFixed(2)}%</span>
              <span>MYR {line.amount}</span>
              <small>{line.notes ?? line.display_formula}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="result-panel">
        <div className="result-panel-heading">
          <GitBranch size={18} />
          <div>
            <span>DECISION TRACE</span>
            <h2>可追溯决策过程</h2>
          </div>
        </div>
        <div className="trace-list">
          {trace.map((item) => (
            <article key={item.sequence_no}>
              <span>{String(item.sequence_no).padStart(2, "0")}</span>
              <div>
                <small>{item.step_type}</small>
                <strong>{item.decision_question}</strong>
                <p>{item.explicit_rationale}</p>
              </div>
              <em>
                {item.human_review_required ? "需人工复核" : "已通过"}
              </em>
            </article>
          ))}
        </div>
      </section>

      <section className="result-panel">
        <div className="result-panel-heading">
          <ShieldCheck size={18} />
          <div>
            <span>MISSING DATA</span>
            <h2>仍需补充的数据</h2>
          </div>
        </div>
        {missing.length ? (
          <div className="missing-result-list">
            {missing.map((item) => (
              <article key={item.field_path}>
                <strong>{item.field_path}</strong>
                <p>{item.description}</p>
                <small>
                  {item.priority} · {item.data_owner} · {item.next_action}
                </small>
              </article>
            ))}
          </div>
        ) : (
          <p className="result-empty">本次Run没有保存阻断性缺失项。</p>
        )}
      </section>
    </main>
  );
}
