"""Policy summarizer — parse condition_expression / formula_expression JSONB
into human-readable Chinese summaries.  Never guesses business meaning;
marks unrecognized patterns as FALLBACK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Domain → tax mapping ────────────────────────────────────────────

DOMAIN_TAX_MAP: dict[str, list[str]] = {
    "IMPORT_DUTY": ["IMPORT_DUTY"],
    "EXCISE": ["EXCISE"],
    "SALES_TAX": ["SALES_TAX"],
    "VAT_GST": ["SALES_TAX"],
    "FTA": ["IMPORT_DUTY"],
    "INCENTIVE": ["IMPORT_DUTY", "EXCISE", "SALES_TAX"],
    "LOCALIZATION": ["EXCISE"],
    "VALUATION": ["IMPORT_DUTY", "EXCISE", "SALES_TAX"],
    "APPROVAL": ["IMPORT_DUTY", "EXCISE", "SALES_TAX"],
}

# ── Field → Chinese label ───────────────────────────────────────────

FIELD_LABELS: dict[str, str] = {
    "vehicle.import_mode": "进口模式",
    "import_mode": "进口模式",
    "vehicle.powertrain": "动力类型",
    "powertrain": "动力类型",
    "vehicle.body_type": "车身类型",
    "body_type": "车身类型",
    "origin_country": "原产国",
    "origin_country_iso2": "原产国",
    "vehicle.category": "车辆类别",
    "displacement_cc": "排量",
    "local_content": "本地化率",
}

VALUE_LABELS: dict[str, str] = {
    "CBU": "CBU（整车进口）",
    "CKD": "CKD（本地组装）",
    "BEV": "BEV（纯电动）",
    "ICE_GASOLINE": "ICE 汽油",
    "ICE_DIESEL": "ICE 柴油",
    "HEV": "HEV（混合动力）",
    "PHEV": "PHEV（插电混动）",
    "EREV": "EREV（增程式）",
    "FCEV": "FCEV（氢燃料）",
    "SEDAN": "轿车",
    "SUV": "SUV",
    "MPV": "MPV",
    "PASSENGER_VEHICLE_8703": "乘用车（87.03）",
}

KNOWN_FORMULA_KEYS: dict[str, str] = {
    "import_duty": "进口关税 = 海关完税价格 × 进口关税率",
    "excise": "消费税 = (海关完税价格 + 进口关税) × 消费税率",
    "sales_tax": "销售税 = (海关完税价格 + 进口关税 + 消费税) × 销售税率",
}

# ── source_type → default evidence_role ─────────────────────────────

SOURCE_TYPE_DEFAULT_ROLE: dict[str, str] = {
    "TARIFF_SCHEDULE": "TARIFF_RATE",
    "OFFICIAL_GUIDE": "TAX_FORMULA",
    "OFFICIAL_PORTAL": "TARIFF_RATE",
    "GAZETTE": "TARIFF_RATE",
    "REGULATION": "TARIFF_RATE",
    "TREATY": "ORIGIN_RULE",
    "BUDGET_DOCUMENT": "INCENTIVE",
    "LAW": "TARIFF_RATE",
}


@dataclass
class PolicySummaries:
    condition_summary: list[str] = field(default_factory=list)
    condition_summary_status: str = "GENERATED"
    formula_summary: list[str] = field(default_factory=list)
    formula_summary_status: str = "GENERATED"
    impact_scope: dict[str, Any] = field(default_factory=dict)
    evidence_roles: dict[str, str] = field(default_factory=dict)  # clause_id → role


def summarize_policy(rule: dict[str, Any]) -> PolicySummaries:
    """Main entry point — parse one rule row into summaries."""
    cond_expr = rule.get("condition_expression") or {}
    formula_expr = rule.get("formula_expression") or {}
    rule_domain = str(rule.get("rule_domain", ""))
    source_type = str(rule.get("source_type", ""))

    # ── Condition summary ──
    cond_lines, cond_status = _parse_condition(cond_expr)

    # ── Formula summary ──
    formula_lines, formula_status = _parse_formula(formula_expr)

    # ── Impact scope ──
    impact = _derive_impact(cond_expr, rule_domain)

    # ── Evidence role ──
    clause_id = str(rule.get("clause_code", ""))
    roles: dict[str, str] = {}
    if clause_id:
        roles[clause_id] = _derive_evidence_role(source_type, rule_domain)

    return PolicySummaries(
        condition_summary=cond_lines,
        condition_summary_status=cond_status,
        formula_summary=formula_lines,
        formula_summary_status=formula_status,
        impact_scope=impact,
        evidence_roles=roles,
    )


# ── Condition parser ────────────────────────────────────────────────


def _parse_condition(expr: dict[str, Any]) -> tuple[list[str], str]:
    """Parse condition_expression JSONB → Chinese label list + status."""
    if not expr:
        return ["适用于所有情况"], "GENERATED"

    try:
        lines: list[str] = []
        _walk_condition(expr, lines)
        if not lines:
            return ["条件表达式见高级信息"], "FALLBACK"
        return lines, "GENERATED"
    except Exception:
        return ["条件表达式见高级信息"], "FALLBACK"


def _walk_condition(node: Any, out: list[str]) -> None:
    """Recursively walk all/any/not/leaf nodes."""
    if isinstance(node, list):
        for item in node:
            _walk_condition(item, out)
        return
    if not isinstance(node, dict):
        return

    # all / any / not containers
    if "all" in node:
        _walk_condition(node["all"], out)
    if "any" in node:
        _walk_condition(node["any"], out)
    if "not" in node:
        _walk_condition(node["not"], out)

    # Leaf: {field, value, operator}
    field = node.get("field")
    value = node.get("value")
    if field and value is not None:
        label = _format_condition_leaf(field, value, node.get("operator", "EQ"))
        out.append(label)


def _format_condition_leaf(field: str, value: Any, operator: str) -> str:
    """Format one condition leaf as a Chinese sentence."""
    f_label = FIELD_LABELS.get(field, field)
    v_label = VALUE_LABELS.get(str(value), str(value))

    if operator in ("EQ", "="):
        return f"适用于{f_label}为 {v_label}"
    if operator in ("NEQ", "!=", "<>"):
        return f"不适用于{f_label}为 {v_label}"
    if operator in ("GT", ">"):
        return f"{f_label} 大于 {v_label}"
    if operator in ("GTE", ">="):
        return f"{f_label} 不小于 {v_label}"
    if operator in ("LT", "<"):
        return f"{f_label} 小于 {v_label}"
    if operator in ("LTE", "<="):
        return f"{f_label} 不大于 {v_label}"
    if operator in ("IN",):
        vals = v_label if isinstance(value, list) else [v_label]
        return f"{f_label} 在 {', '.join(str(v) for v in vals)} 范围内"
    return f"{f_label}: {v_label}"


# ── Formula parser ──────────────────────────────────────────────────


def _parse_formula(expr: dict[str, Any]) -> tuple[list[str], str]:
    """Parse formula_expression JSONB → Chinese formula list + status."""
    if not expr:
        return [], "GENERATED"

    lines: list[str] = []
    recognized = 0

    for key, chinese in KNOWN_FORMULA_KEYS.items():
        if key in expr:
            lines.append(chinese)
            recognized += 1

    if recognized == 0:
        # Try generic: iterate keys
        for key in expr:
            if isinstance(expr[key], str):
                lines.append(f"{key} = {expr[key]}")
        if not lines:
            lines.append("计算逻辑见高级信息")
        return lines, "FALLBACK"

    return lines, "GENERATED"


# ── Impact scope derivation ─────────────────────────────────────────


def _derive_impact(cond_expr: dict[str, Any], domain: str) -> dict[str, Any]:
    """Derive impact_scope from condition_expression + rule_domain.

    Priority:
      1. Explicit condition_expression fields (vehicle_mode, powertrain)
      2. rule_domain → taxes mapping
      3. Falls back to null (unknown) when unresolvable
    """
    modes: list[str] | None = None
    powertrains: list[str] | None = None

    # Priority 1: extract from condition_expression
    flat: list[dict[str, Any]] = []
    _flatten_leaves(cond_expr, flat)

    mode_values: list[str] = []
    pt_values: list[str] = []
    for leaf in flat:
        f = leaf.get("field", "")
        v = leaf.get("value")
        if f in ("vehicle.import_mode", "import_mode") and v:
            mode_values.append(str(v))
        if f in ("vehicle.powertrain", "powertrain") and v:
            pt_values.append(str(v))

    if mode_values:
        modes = mode_values
    if pt_values:
        powertrains = pt_values

    # Priority 2: domain → taxes
    taxes: list[str] | None = DOMAIN_TAX_MAP.get(domain)

    return {
        "vehicle_modes": modes,
        "powertrains": powertrains,
        "taxes": taxes,
    }


def _flatten_leaves(node: Any, out: list[dict[str, Any]]) -> None:
    """Flatten nested all/any/not → flat list of leaf dicts."""
    if isinstance(node, list):
        for item in node:
            _flatten_leaves(item, out)
        return
    if not isinstance(node, dict):
        return
    if "all" in node:
        _flatten_leaves(node["all"], out)
    if "any" in node:
        _flatten_leaves(node["any"], out)
    if "not" in node:
        _flatten_leaves(node["not"], out)
    if "field" in node and "value" in node:
        out.append(node)


# ── Evidence role derivation ────────────────────────────────────────


def _derive_evidence_role(source_type: str, rule_domain: str) -> str:
    """Infer evidence_role from source_type + rule_domain.

    MVP: resolver-generated. Future: DB table evidence.source_clause_role.
    """
    default = SOURCE_TYPE_DEFAULT_ROLE.get(source_type, "TARIFF_RATE")

    # Override: OFFICIAL_GUIDE + FTA domain → ORIGIN_RULE
    if source_type == "OFFICIAL_GUIDE" and rule_domain == "FTA":
        return "ORIGIN_RULE"

    # Override: GAZETTE + INCENTIVE domain → INCENTIVE
    if source_type == "GAZETTE" and rule_domain == "INCENTIVE":
        return "INCENTIVE"

    # Override: BUDGET_DOCUMENT → INCENTIVE
    if source_type == "BUDGET_DOCUMENT":
        return "INCENTIVE"

    return default
