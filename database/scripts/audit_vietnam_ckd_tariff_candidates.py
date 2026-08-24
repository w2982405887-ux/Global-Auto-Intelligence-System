"""Audit Vietnam CKD major-parts tariff candidates.

This audit intentionally reproduces the retired "lowest duty rate per CCU"
selection and explains why it must not be used as a customs-classification
method.  It writes a concise Markdown report for review after every tariff
extract refresh.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "docs" / "audits" / "vietnam_ckd_candidate_selection_audit.md"


def risk_reason(ccu: str, description: str, excluded: list[str]) -> str:
    value = description.upper()
    if "CN" in {item.upper() for item in excluded}:
        return f"中国原产被排除：{', '.join(excluded)}"
    if any(token in value for token in ("87.11", "MOTORCYCLE", "MOTOR CYCLE", "MÔ TÔ", "XE MÁY")):
        return "摩托车用途，不能用于乘用车 CKD"
    if any(token in value for token in ("87.01", "TRACTOR", "MÁY KÉO")):
        return "拖拉机用途，不能用于乘用车 CKD"
    if ccu == "VN-CKD-BODY" and ("87.02" in value or "87.04" in value):
        return "客车/货车用途，不能用于乘用车车身"
    if any(token in value for token in ("OTHER", "LOẠI KHÁC", "KHÁC")):
        return "宽泛“其他”税目；需要零件技术状态后才能确认"
    if excluded:
        return f"存在其他原产地排除（{', '.join(excluded)}）；仍须确认技术事实"
    return "需以零件技术状态、用途及海关归类意见确认"


def main() -> int:
    url = os.environ.get("GAIS_DATABASE_URL")
    if not url:
        raise SystemExit("Set GAIS_DATABASE_URL before running this audit.")
    engine = create_engine(url)
    with engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT DISTINCT ON (ccu.ccu_code)
                   ccu.ccu_code, ccu.ccu_name_cn, m.national_tariff_code,
                   m.duty_rate, m.tariff_description,
                   COALESCE(m.eligibility_condition->'excluded_origin_countries', '[]'::jsonb) AS excluded
            FROM customs.tariff_mapping m
            JOIN ref.country country ON country.country_id=m.country_id
            JOIN ref.trade_agreement agreement ON agreement.trade_agreement_id=m.trade_agreement_id
            JOIN customs.ccu_candidate_hs candidate ON candidate.candidate_id=m.candidate_id
            JOIN customs.customs_classification_unit ccu ON ccu.ccu_id=candidate.ccu_id
            WHERE country.iso2='VN' AND agreement.agreement_code='ACFTA'
              AND m.eligibility_condition->>'origin_group'='CN'
              AND m.record_status='ACTIVE'
              AND m.effective_from<=:as_of AND (m.effective_to IS NULL OR m.effective_to>:as_of)
            ORDER BY ccu.ccu_code, m.duty_rate ASC NULLS LAST, m.national_tariff_code
        """), {"as_of": date(2027, 10, 11)}).mappings().all()

    lines = [
        "# 越南 CKD 主要部件候选税号审计",
        "",
        "审计日期：2026-08-11；场景：越南、原产中国、ACFTA、2027-10-11。",
        "",
        "本报告复现旧逻辑“每个部件挑最低关税候选”。该逻辑已禁用；下面任何一行均**不是**可直接用于报关或计算的最终税号。",
        "",
        "| 部件 | 旧逻辑最低候选 | 候选税率 | 审计结论 |",
        "|---|---:|---:|---|",
    ]
    for row in rows:
        excluded = list(row["excluded"] or [])
        reason = risk_reason(row["ccu_code"], row["tariff_description"] or "", excluded)
        duty = "—" if row["duty_rate"] is None else f"{float(row['duty_rate']) * 100:g}%"
        lines.append(f"| {row['ccu_name_cn']} | {row['national_tariff_code']} | {duty} | {reason} |")
    lines += [
        "",
        "## 修复后的控制",
        "",
        "- 不再按最低税率自动挑选税号。",
        "- 将官方附件中的 `excluded_origin_countries` 写入候选行；例如中国被排除时，不会在中国原产场景中展示或计算该行。",
        "- 显式排除已写明摩托车、拖拉机、客车/货车用途的候选。",
        "- 必须由使用者依据部件技术状态选择最终越南税号；未选齐时系统不输出进口关税率。",
        "- 即使所有税号已选，结果仍是“候选测算”，还需原产地规则、证明文件、BOM价值和 GRI 2(a)风险审查。",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
