"use client";

import { CircleAlert, LoaderCircle, Plus, Scale, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  type BomComparisonResult,
  type CcuCatalogItem,
  type CcuTariffOption,
  type DecisionProject,
  type ProjectBomResponse,
  getCcuCatalog,
  getCcuTariffOptions,
  getProjectBom,
  previewProjectBomComparison,
  runProjectBomComparison,
  saveProjectBomLine,
  saveProjectBomMapping,
} from "../../lib/api";

const regimes = ["MFN", "ACFTA", "RCEP"] as const;

export default function ProjectBomPanel({
  project,
}: {
  project: DecisionProject;
}) {
  const [catalog, setCatalog] = useState<CcuCatalogItem[]>([]);
  const [bom, setBom] = useState<ProjectBomResponse | null>(null);
  const [options, setOptions] = useState<CcuTariffOption[]>([]);
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [comparison, setComparison] = useState<BomComparisonResult | null>(null);
  const [savedRunCodes, setSavedRunCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({
    enterprise_part_no: "",
    part_name: "",
    ccu_code: "",
    customs_value: "",
    quantity: "1",
    origin_country_iso2: "CN",
    local_or_imported: "IMPORTED" as "IMPORTED" | "LOCAL",
    enterprise_inputs_complete: false,
    gri_2a_review_complete: false,
  });

  useEffect(() => {
    Promise.all([getCcuCatalog(), getProjectBom(project.project_id)])
      .then(([ccus, currentBom]) => {
        setCatalog(ccus.items);
        setBom(currentBom);
      })
      .catch((cause) =>
        setError(cause instanceof Error ? cause.message : "BOM数据加载失败"),
      );
  }, [project.project_id]);

  const regimeOptions = useMemo(
    () =>
      Object.fromEntries(
        regimes.map((regime) => [
          regime,
          options.filter((option) =>
            regime === "MFN"
              ? option.origin_regime === "MFN"
              : option.agreement_code === regime,
          ),
        ]),
      ) as Record<(typeof regimes)[number], CcuTariffOption[]>,
    [options],
  );

  async function chooseCcu(ccuCode: string) {
    setDraft((current) => ({ ...current, ccu_code: ccuCode }));
    setSelections({});
    setComparison(null);
    if (!ccuCode) {
      setOptions([]);
      return;
    }
    try {
      const result = await getCcuTariffOptions(
        ccuCode,
        project.calculation_date,
      );
      setOptions(result.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "税率候选加载失败");
    }
  }

  async function saveLineAndMappings() {
    if (
      !draft.enterprise_part_no ||
      !draft.ccu_code ||
      !draft.customs_value
    ) {
      setError("请填写料号、CCU和海关价值。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const lineNo = (bom?.items.length ?? 0) + 1;
      const saved = await saveProjectBomLine(project.project_id, lineNo, {
        enterprise_part_no: draft.enterprise_part_no,
        part_name: draft.part_name || null,
        ccu_code: draft.ccu_code,
        customs_value: draft.customs_value,
        quantity: draft.quantity,
        currency_code: "MYR",
        origin_country_iso2: draft.origin_country_iso2,
        local_or_imported: draft.local_or_imported,
        enterprise_inputs_complete: draft.enterprise_inputs_complete,
        gri_2a_review_complete: draft.gri_2a_review_complete,
      });
      let nextBom = saved.bom;
      if (draft.local_or_imported === "IMPORTED") {
        for (const regime of regimes) {
          const mappingCode = selections[regime];
          if (mappingCode) {
            const result = await saveProjectBomMapping(
              project.project_id,
              lineNo,
              regime,
              mappingCode,
            );
            nextBom = result.bom;
          }
        }
      }
      setBom(nextBom);
      setDraft({
        enterprise_part_no: "",
        part_name: "",
        ccu_code: "",
        customs_value: "",
        quantity: "1",
        origin_country_iso2: "CN",
        local_or_imported: "IMPORTED",
        enterprise_inputs_complete: false,
        gri_2a_review_complete: false,
      });
      setOptions([]);
      setSelections({});
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "BOM行保存失败");
    } finally {
      setBusy(false);
    }
  }

  async function calculateComparison() {
    setBusy(true);
    setError(null);
    try {
      setComparison(await previewProjectBomComparison(project.project_id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "BOM比较失败");
    } finally {
      setBusy(false);
    }
  }

  async function saveComparisonRun() {
    setBusy(true);
    setError(null);
    try {
      const response = await runProjectBomComparison(project.project_id);
      setComparison(response.result);
      setSavedRunCodes(response.audit.runs.map((run) => run.run_code));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "正式计算保存失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="bom-panel">
      <div className="bom-panel-heading">
        <div>
          <span>PROJECT BOM / CCU</span>
          <h3>项目BOM价值分配</h3>
        </div>
        <strong>{bom?.summary.line_count ?? 0} 条</strong>
      </div>
      {error && (
        <div className="decision-message error">
          <CircleAlert size={16} />
          {error}
        </div>
      )}
      <div className="bom-form-grid">
        <label>
          企业料号
          <input
            value={draft.enterprise_part_no}
            onChange={(event) =>
              setDraft({ ...draft, enterprise_part_no: event.target.value })
            }
            placeholder="例如 BRAKE-PAD-001"
          />
        </label>
        <label>
          零件名称
          <input
            value={draft.part_name}
            onChange={(event) =>
              setDraft({ ...draft, part_name: event.target.value })
            }
            placeholder="企业可读名称"
          />
        </label>
        <label className="wide">
          Customs Classification Unit（海关归类单元）
          <select
            value={draft.ccu_code}
            onChange={(event) => chooseCcu(event.target.value)}
          >
            <option value="">选择CCU</option>
            {catalog.map((ccu) => (
              <option key={ccu.ccu_code} value={ccu.ccu_code}>
                {ccu.ccu_code} · {ccu.ccu_name_cn}
              </option>
            ))}
          </select>
        </label>
        <label>
          海关价值（MYR）
          <input
            type="number"
            min="0"
            value={draft.customs_value}
            onChange={(event) =>
              setDraft({ ...draft, customs_value: event.target.value })
            }
          />
        </label>
        <label>
          数量
          <input
            type="number"
            min="0.000001"
            value={draft.quantity}
            onChange={(event) =>
              setDraft({ ...draft, quantity: event.target.value })
            }
          />
        </label>
      </div>
      {options.length > 0 && (
        <div className="bom-regime-grid">
          {regimes.map((regime) => (
            <label key={regime}>
              {regime}税率映射
              <select
                value={selections[regime] ?? ""}
                onChange={(event) =>
                  setSelections({
                    ...selections,
                    [regime]: event.target.value,
                  })
                }
              >
                <option value="">显式选择</option>
                {regimeOptions[regime].map((option) => (
                  <option key={option.mapping_code} value={option.mapping_code}>
                    {option.national_tariff_code} ·{" "}
                    {option.duty_rate == null
                      ? "税率缺失"
                      : `${Number(option.duty_rate) * 100}%`}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      )}
      <div className="bom-checks">
        <label>
          <input
            type="checkbox"
            checked={draft.enterprise_inputs_complete}
            onChange={(event) =>
              setDraft({
                ...draft,
                enterprise_inputs_complete: event.target.checked,
              })
            }
          />
          企业技术参数已完整
        </label>
        <label>
          <input
            type="checkbox"
            checked={draft.gri_2a_review_complete}
            onChange={(event) =>
              setDraft({
                ...draft,
                gri_2a_review_complete: event.target.checked,
              })
            }
          />
          GRI 2(a)装运层审核完成
        </label>
      </div>
      <button
        type="button"
        className="decision-secondary"
        disabled={busy}
        onClick={saveLineAndMappings}
      >
        {busy ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />}
        保存BOM行与税率选择
      </button>
      {(bom?.items.length ?? 0) > 0 && (
        <>
          <div className="bom-table">
            {bom?.items.map((line) => (
              <article key={line.project_bom_line_id}>
                <strong>
                  {line.line_no}. {line.enterprise_part_no}
                </strong>
                <span>{line.ccu_code}</span>
                <span>MYR {line.customs_value}</span>
                <small>{Object.keys(line.selections).join(" / ") || "未选税率"}</small>
              </article>
            ))}
          </div>
          <button
            type="button"
            className="decision-primary"
            disabled={busy}
            onClick={calculateComparison}
          >
            {busy ? <LoaderCircle className="spin" size={16} /> : <Scale size={16} />}
            比较MFN、ACFTA与RCEP
          </button>
        </>
      )}
      {comparison && (
        <div className="bom-comparison-grid">
          {comparison.scenarios.map((scenario) => (
            <article key={scenario.requested_regime}>
              <span>{scenario.requested_regime}</span>
              <strong>
                {scenario.net_import_tax == null
                  ? "BLOCKED"
                  : `MYR ${scenario.net_import_tax}`}
              </strong>
              <small>{scenario.completeness}</small>
              <p>
                有效净税率：
                {scenario.effective_net_tax_rate == null
                  ? "—"
                  : `${(Number(scenario.effective_net_tax_rate) * 100).toFixed(2)}%`}
              </p>
            </article>
          ))}
          <div className="bom-recommendation">
            <Save size={16} />
            当前最低净进口税：
            <strong>
              {comparison.decision_summary.lowest_net_tax_requested_regime ??
                "尚不可排名"}
            </strong>
          </div>
          <button
            type="button"
            className="decision-secondary"
            disabled={busy}
            onClick={saveComparisonRun}
          >
            {busy ? <LoaderCircle className="spin" size={15} /> : <Save size={15} />}
            保存正式计算与审计轨迹
          </button>
          {savedRunCodes.length > 0 && (
            <p className="bom-run-codes">
              已保存：{savedRunCodes.join(" / ")}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
