"""LangGraph Agent — simplified message-passing loop.

Avoids add_messages reducer complexity: each node reads all messages from state,
appends its own, and returns the full list. Tool calls are detected and executed
manually to avoid tool_call_id matching issues with different LLM providers.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from app.agent.guard import sanitize_external_context
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.provider import LLMProvider
from app.agent.schema import AgentAnswer, ToolResultEnvelope
from app.agent.state import AgentState
from app.agent.tools.cbu_tool import calculate_cbu_tax
from app.agent.tools.ckd_tool import calculate_ckd_tax
from app.agent.tools.coverage_tool import inspect_data_coverage
from app.agent.tools.evidence_tool import get_policy_evidence
from app.agent.tools.policy_tool import search_policy_rules

ALL_TOOLS = [calculate_cbu_tax, calculate_ckd_tax, search_policy_rules, get_policy_evidence, inspect_data_coverage]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}

MAX_STEPS = 8
MAX_TOOLS = 6


def _tool_desc() -> str:
    lines = []
    for t in ALL_TOOLS:
        desc = (t.description or "").split("\n")[0][:200]
        lines.append(f"- **{t.name}**: {desc}")
    return "\n".join(lines)


TOOL_SECTION = f"""
You have access to the following tools:

{_tool_desc()}

To call a tool, output a JSON block EXACTLY like this at the end of your response:

```tool_call
[{{"name": "tool_name", "arguments": {{...}}}}]
```

You may call multiple tools. The system will execute them and append the results.
When you have enough information, give your final answer WITHOUT a tool_call block.
"""


def _build_messages(state: AgentState, step: int) -> list:
    existing = _history_messages(state.get("messages", []))

    # The system prompt is an invocation concern, not persisted chat history.
    # It must be present on *every* model round: after a tool result the graph
    # loops back to the agent node, and omitting the prompt there removes the
    # tool-call protocol entirely.  This was the reason the model often said
    # “I will query the tool” but returned no call on the next round.
    ctx = state.get("confirmed_context", {})
    goal = state.get("user_goal", "")
    extra = f"\nCurrent agent round: {step + 1}.\n"
    if goal:
        extra += f"\nCurrent user goal: {goal}\n"
    if ctx:
        extra += f"\nCONFIRMED: {json.dumps(ctx, ensure_ascii=False)}\n"
    if state.get("force_final_answer"):
        extra += (
            "\nFINAL SYNTHESIS ROUND: tools have already been executed for this user turn. "
            "Answer the user's actual question using the [Tool result: ...] messages below. "
            "Do not emit a tool_call block, do not say that you will call a tool, and do not "
            "reuse a prior answer. If the question asks for conditions, explain conditions; "
            "if it asks for rates, explain the returned candidate rates and their limitations.\n"
            "Evidence gate: only an INTERNAL_VERIFIED calculator result may establish a "
            "numeric tax rate. EXTERNAL_UNVERIFIED search results can only corroborate. "
            "Keep candidate/未入库/未匹配/待归类/不适用 labels exact, separate incentives "
            "from MFN/FTA, and state that 0% import duty is not 0% comprehensive tax.\n"
        )
    return [SystemMessage(content=SYSTEM_PROMPT + TOOL_SECTION + extra)] + existing


def _is_system_prompt_leak(content: str) -> bool:
    return (
        "You are the AutoPolicy Global Automotive Export Decision Assistant" in content
        or "You have access to the following tools:" in content
    )


def _history_messages(messages: list) -> list:
    """Keep persisted chat history free of system prompts and prompt echoes."""
    cleaned = []
    for msg in messages:
        msg_type = getattr(msg, "type", "")
        content = getattr(msg, "content", "")
        if msg_type == "system":
            continue
        if isinstance(content, str) and _is_system_prompt_leak(content):
            continue
        cleaned.append(msg)
    return cleaned


# ── Evidence gate ─────────────────────────────────────────────────

# These labels are deliberately kept in the Agent layer instead of inferred by
# the model.  A policy-search hit and a calculator result have different
# evidentiary authority, even when both contain a percentage.
_TAX_TOOL_NAMES = {"calculate_cbu_tax", "calculate_ckd_tax"}
_EXTERNAL_SEARCH_TOOL_NAMES = {"gais_web_search", "web_search", "openai_web_search"}
_VERIFIED_STATUSES = {"VERIFIED", "RULING_CONFIRMED", "STATUTORY_CHAIN_COMPLETE"}
_RATE_MARKERS = (
    "税率", "税负", "关税", "综合税率", "消费税", "销售税", "税额",
    "多少", "tax", "duty", "rate", "tax burden", "excise", "sales tax",
)


def _is_explicit_rate_question(text: str) -> bool:
    """Return True for a request for a numeric tax/rate result.

    This is intentionally conservative: a question about *conditions* must not
    be converted into a calculator answer merely because it contains the word
    “税率”.
    """

    if _is_condition_question(text):
        return False
    lowered = text.lower()
    return any(marker in text or marker in lowered for marker in _RATE_MARKERS)


def _verification_statuses(value: Any) -> set[str]:
    statuses: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "verification_status" and item is not None:
                statuses.add(str(item).strip().upper())
            else:
                statuses.update(_verification_statuses(item))
    elif isinstance(value, list):
        for item in value:
            statuses.update(_verification_statuses(item))
    return statuses


def _calculator_scope(tool_name: str, result: dict[str, Any]) -> tuple[str, bool]:
    """Return (scope, complete) without treating candidate rows as final.

    CBU can expose a complete statutory chain.  CKD commonly has a complete
    *import-stage* result but an unavailable local-assembly/full-cycle result;
    that distinction is material for the decision assistant.
    """

    if tool_name not in _TAX_TOOL_NAMES:
        return "NONE", False

    # Explicit tool flags take precedence over shape-based compatibility with
    # older calculator payloads.
    if result.get("applicability_status") in {
        "UNSUPPORTED_COUNTRY", "CLASSIFICATION_SELECTION_REQUIRED", "CANDIDATE_REGIMES",
    }:
        return "NONE", False

    if result.get("is_complete_statutory_chain") is True:
        return "FULL_CHAIN", True

    combined = result.get("combined_results")
    if isinstance(combined, list) and combined:
        complete = any(
            isinstance(item, dict)
            and item.get("is_complete") is True
            and item.get("effective_tax_rate") is not None
            for item in combined
        )
        if complete:
            return "FULL_CHAIN", True

    paths = result.get("paths")
    if isinstance(paths, list):
        for path in paths:
            if not isinstance(path, dict):
                continue
            statutory = path.get("statutory") or {}
            if statutory.get("is_complete_statutory_chain") is True:
                return "FULL_CHAIN", True

    # The CKD import-stage result is useful and deterministic even when the
    # local-assembly stage is deliberately outside the current scope.
    if tool_name == "calculate_ckd_tax":
        import_stage = result.get("import_stage") or {}
        effective_rates = import_stage.get("import_effective_rates")
        if isinstance(effective_rates, list) and effective_rates:
            usable = [
                row for row in effective_rates
                if isinstance(row, dict)
                and row.get("import_effective_rate") is not None
            ]
            if usable and result.get("full_cycle_available") is not True:
                return "IMPORT_STAGE", True

    return "NONE", False


def _semantic_result_status(tool_name: str, result: dict[str, Any]) -> str:
    """Normalize result semantics for the model and UI.

    The distinction is part of the contract: an absent database row is not the
    same thing as a row that failed to match, a classification awaiting ruling,
    or a rule that does not apply to the requested origin/country.
    """

    raw_status = str(
        result.get("applicability_status")
        or result.get("status")
        or ""
    ).upper()
    if raw_status in {"UNSUPPORTED_COUNTRY", "NOT_APPLICABLE", "INAPPLICABLE"}:
        return "NOT_APPLICABLE"
    if raw_status in {"CLASSIFICATION_SELECTION_REQUIRED", "SCENARIO_MATCHED_CLASSIFICATION_PENDING"}:
        return "PENDING_CLASSIFICATION"
    if raw_status in {"CANDIDATE_REGIMES", "CANDIDATE", "CANDIDATES"}:
        return "CANDIDATE_CONDITIONAL"
    if raw_status in {"NOT_FOUND", "NO_DATA", "NOT_IN_DATABASE"}:
        return "NOT_IN_DATABASE"
    if tool_name in _EXTERNAL_SEARCH_TOOL_NAMES:
        if result.get("status") == "NOT_CONFIGURED":
            return "SEARCH_NOT_CONFIGURED"
        return "SEARCH_ONLY"
    if tool_name == "search_policy_rules":
        return "VERIFIED_POLICY" if int(result.get("total") or 0) > 0 else "NOT_MATCHED"
    if tool_name == "get_policy_evidence":
        return "OFFICIAL_EVIDENCE" if result.get("status") == "FOUND" else "NOT_IN_DATABASE"

    # CKD may deliberately report local-assembly SCT/VAT as missing while its
    # import-stage rows are complete.  Preserve that usable scope instead of
    # downgrading the import-duty result to a generic mismatch.
    scope, complete = _calculator_scope(tool_name, result)
    if complete:
        return "VERIFIED_RESULT"

    missing = result.get("missing_information") or result.get("missing_items") or []
    if missing:
        # A calculator can return PARTIAL even when the reason is specifically
        # that the tariff row is not in the local database.
        joined = " ".join(str(item) for item in missing).lower()
        if any(token in joined for token in ("未入库", "not in database", "no usable row", "尚未入库")):
            return "NOT_IN_DATABASE"
        if any(token in joined for token in ("不适用", "not applicable", "unsupported")):
            return "NOT_APPLICABLE"
        if any(token in joined for token in ("归类", "classification", "tax_code")):
            return "PENDING_CLASSIFICATION"
        return "NOT_MATCHED"
    return "VERIFIED_RESULT" if _calculator_scope(tool_name, result)[1] else "PARTIAL"


def _evidence_gate(tool_name: str, result: Any) -> dict[str, Any]:
    """Build a machine-readable evidence contract for each tool result."""

    payload = result if isinstance(result, dict) else {"value": result}
    semantic_status = _semantic_result_status(tool_name, payload)
    scope, complete = _calculator_scope(tool_name, payload)
    statuses = _verification_statuses(payload)
    has_evidence = bool(payload.get("evidence_refs"))
    # Existing MY calculators predate a top-level verification_status but carry
    # complete combined rows and source evidence.  Treat that explicit chain as
    # verified while keeping candidates/partial rows blocked above.
    internally_verified = bool(
        tool_name in _TAX_TOOL_NAMES
        and complete
        and semantic_status == "VERIFIED_RESULT"
        and (bool(statuses & _VERIFIED_STATUSES) or has_evidence or scope == "IMPORT_STAGE")
    )
    if tool_name in _EXTERNAL_SEARCH_TOOL_NAMES:
        tier = "EXTERNAL_UNVERIFIED"
    elif tool_name == "search_policy_rules":
        tier = "INTERNAL_VERIFIED_POLICY" if semantic_status == "VERIFIED_POLICY" else "INTERNAL_NO_MATCH"
    elif internally_verified:
        tier = "INTERNAL_VERIFIED"
    elif tool_name == "get_policy_evidence":
        tier = "OFFICIAL_EVIDENCE" if semantic_status == "OFFICIAL_EVIDENCE" else "INTERNAL_NO_MATCH"
    else:
        tier = "INTERNAL_INCOMPLETE"

    candidate_only = semantic_status in {"CANDIDATE_CONDITIONAL", "PENDING_CLASSIFICATION"}
    zero_rate_warning = bool(
        any(
            str(item.get("rate") or item.get("import_duty_rate") or "") in {"0", "0.0", "0.00", "0.0000"}
            for item in payload.get("import_duty_options", [])
            if isinstance(item, dict)
        )
        or "零关税" in json.dumps(payload, ensure_ascii=False)
    )
    return {
        "semantic_status": semantic_status,
        "source_tier": tier,
        "scope": scope,
        "can_confirm_numeric_rates": internally_verified,
        "candidate_only": candidate_only,
        "web_search_may_override": False,
        "zero_rate_is_not_total_burden": zero_rate_warning,
        "verification_statuses": sorted(statuses),
        "evidence_refs_count": len(payload.get("evidence_refs") or []),
    }


def _evidence_gated_tool_message(tool_name: str, result: dict[str, Any]) -> str:
    """Serialize a tool result with a non-optional provenance header."""

    gate = _evidence_gate(tool_name, result)
    return (
        f"[Tool result: {tool_name}]\n"
        "[EVIDENCE_GATE — machine rules are authoritative]\n"
        f"{json.dumps(gate, ensure_ascii=False)}\n"
        "[END_EVIDENCE_GATE]\n"
        f"{json.dumps(result, ensure_ascii=False, default=str)[:120000]}\n"
        f"[/Tool: {tool_name}]"
    )


def _apply_final_evidence_gate(content: str, state: AgentState, user_text: str) -> str:
    """Prevent an incomplete/search-only round from looking like a final rate.

    This is a last-resort UI safety net; the system prompt and gated tool
    messages remain the primary controls.  It intentionally does not invent a
    replacement number or delete the model's explanation.
    """

    if not _is_explicit_rate_question(user_text):
        return content
    records = state.get("tool_results", {}) or {}
    gates = []
    for envelope in records.values() if isinstance(records, dict) else []:
        if not isinstance(envelope, dict):
            continue
        name = str(envelope.get("tool_name") or "")
        result = envelope.get("result")
        if isinstance(result, dict):
            gates.append(_evidence_gate(name, result))
    has_verified = any(gate.get("can_confirm_numeric_rates") for gate in gates)
    guarded = content.strip()
    if not has_verified:
        prefix = (
            "⚠️ 证据门禁：当前内部计算器没有返回该问题所需的完整、已核验税率结果。"
            "联网搜索或候选税号只能用于线索/核验，不能作为确定税率；请按下方缺失状态补充后再定值。\n\n"
        )
        if not guarded.startswith("⚠️ 证据门禁"):
            guarded = prefix + guarded
    if ("0%" in guarded or "零关税" in guarded or "0％" in guarded) and "不等于综合税负" not in guarded:
        guarded += "\n\n注：0%仅表示对应进口税行（如适用条件成立）的税率，不等于综合税负为0%，也不等于整车或全流程税负为0%。"
    return guarded


def _parse_tool_calls(content: str) -> list[dict] | None:
    """Extract tool_call JSON blocks from LLM response."""
    if "tool_call" not in content and '"name"' not in content:
        return None

    patterns = [
        r"```tool_call\s*(.*?)```",
        r"```(?:json)?\s*(\[\s*\{\s*\"name\".*?\}\s*\])\s*```",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, flags=re.DOTALL)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            parsed = [parsed]
        if isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed):
            return parsed
    return None


def _clean_content(content: str) -> str:
    """Remove tool_call blocks and prompt echoes from displayed content."""
    cleaned = re.sub(r"```tool_call\s*.*?(?:```|$)", "", content, flags=re.DOTALL)
    cleaned = re.sub(
        r"```(?:json)?\s*\[\s*\{\s*\"name\".*?\}\s*\]\s*(?:```|$)",
        "",
        cleaned,
        flags=re.DOTALL,
    )
    if _is_system_prompt_leak(cleaned):
        cleaned = cleaned.split("You are the AutoPolicy", 1)[0]
    return cleaned.strip()


def _last_user_text(messages: list) -> str:
    for msg in reversed(messages):
        if getattr(msg, "type", "") == "human":
            content = getattr(msg, "content", "")
            if isinstance(content, str):
                return content
    return ""



def _seed_tool_calls(state: AgentState, messages: list) -> list[dict] | None:
    """Deterministically start only the simplest Malaysia BEV CBU/CKD comparison."""
    if state.get("step_count", 0) != 0 or state.get("tool_call_count", 0):
        return None

    text = _last_user_text(messages)
    lowered = text.lower()

    if "cbu" not in lowered or "ckd" not in lowered:
        return None
    if not ("malaysia" in lowered or "马来西亚" in text):
        return None
    if "bev" not in lowered and "纯电" not in text and "电动" not in text:
        return None

    # Anything requiring explanation, exact rates, a different powertrain, or
    # additional vehicle attributes should be handled by the normal LLM/tool path.
    complex_markers = (
        "erev", "phev", "hev", "ice",
        "增程", "续航", "排量",
        "为什么", "为何", "原因",
        "多少", "分别", "综合税率",
        "why", "reason", "exact", "rate",
    )
    if any(marker in lowered or marker in text for marker in complex_markers):
        return None

    if not (
        "哪个税负更低" in text
        or "哪个更低" in text
        or "which" in lowered
        or "lower" in lowered
    ):
        return None

    origin_country = "CN" if ("中国" in text or "china" in lowered) else None
    args = {
        "country": "MY",
        "origin_country": origin_country,
        "powertrain": "BEV",
        "effective_date": str(date.today()),
    }
    return [
        {"name": "calculate_cbu_tax", "arguments": args},
        {"name": "calculate_ckd_tax", "arguments": args},
    ]



def _infer_request_args(text: str) -> dict[str, Any]:
    lowered = text.lower()
    powertrain = "BEV"
    if "erev" in lowered or "增程" in text:
        direct_drive_markers = ("可直驱", "机械驱动", "机械连接", "发动机能驱动", "发动机参与驱动", "发动机驱动车轮", "汽油增程")
        series_only_markers = ("仅发电", "只发电", "纯串联", "车轮只由电机", "发动机不驱动")
        if any(m in text for m in direct_drive_markers):
            powertrain = "PHEV"
        elif any(m in text for m in series_only_markers):
            powertrain = "EREV"
        else:
            powertrain = "EREV"
    elif "phev" in lowered or "插混" in text or "插电" in text:
        powertrain = "PHEV"
    elif "hev" in lowered or "混动" in text:
        powertrain = "HEV"
    elif "柴油" in text or "diesel" in lowered:
        powertrain = "ICE_DIESEL"
    elif "ice" in lowered or "燃油" in text or "汽油" in text:
        powertrain = "ICE_GASOLINE"

    origin_country = "CN" if ("中国" in text or "china" in lowered) else None

    body_type = "SEDAN"
    if "suv" in lowered or "越野" in text:
        body_type = "SUV"
    elif "mpv" in lowered or "多用途" in text:
        body_type = "MPV"
    elif "hatchback" in lowered or "两厢" in text:
        body_type = "HATCHBACK"
    elif "wagon" in lowered or "旅行" in text:
        body_type = "WAGON"
    elif "coupe" in lowered or "轿跑" in text:
        body_type = "COUPE"
    elif "轿车" in text or "sedan" in lowered:
        body_type = "SEDAN"

    drive_type = "4WD_AWD"
    if "4wd" in lowered or "awd" in lowered or "四驱" in text or "全驱" in text:
        drive_type = "4WD_AWD"

    displacement_cc = None
    displacement_match = re.search(r"(\d+(?:\.\d+)?)\s*[lL升]", text)
    if displacement_match:
        displacement_cc = int(float(displacement_match.group(1)) * 1000)
    else:
        cc_match = re.search(r"(\d{3,5})\s*(?:cc|CC|毫升)", text)
        if cc_match:
            displacement_cc = int(cc_match.group(1))

    return {
        "country": "MY",
        "origin_country": origin_country,
        "powertrain": powertrain,
        "displacement_cc": displacement_cc,
        "body_type": body_type,
        "drive_type": drive_type,
        "effective_date": str(date.today()),
    }


def _is_condition_question(text: str) -> bool:
    """Classify questions asking *what affects eligibility*, not a rate.

    This guard is deliberately conservative.  The word “关税/税” alone must
    not trigger a calculator: users often ask for the conditions that affect a
    duty rate.  A calculator is only appropriate when the message also asks
    for a numeric result or an explicit calculation.
    """
    lowered = text.lower()
    condition_markers = (
        "影响条件", "影响因素", "条件有哪些", "需要哪些条件", "适用条件", "资格条件",
        "筛选条件", "判断条件", "取决于什么", "决定什么", "哪些因素", "怎么判断",
        "不是具体税率", "不是税率", "不要税率", "只想知道条件", "条件是什么",
        "what conditions", "eligibility", "qualifying conditions", "what factors", "depends on",
    )
    numeric_markers = (
        "多少", "税率", "税负", "综合税率", "计算", "算一下", "测算", "估算", "金额",
        "rate", "tax burden", "calculate", "compute", "estimate", "how much",
    )
    has_condition = any(marker in text or marker in lowered for marker in condition_markers)
    has_numeric_request = any(marker in text or marker in lowered for marker in numeric_markers)
    # Explicit negations such as “不是具体税率” override the generic “税率”
    # token that appears inside the sentence.
    explicit_condition_only = any(
        marker in text or marker in lowered
        for marker in ("不是具体税率", "不是税率", "只想知道条件", "what conditions", "eligibility")
    )
    return has_condition and (explicit_condition_only or not has_numeric_request)


def _condition_route_tool_calls(text: str) -> list[dict]:
    args = _infer_request_args(text)
    lowered = text.lower()
    has_cbu = "cbu" in lowered or "整车进口" in text or "整车" in text
    has_ckd = "ckd" in lowered or "散件" in text or "零件组装" in text
    import_mode = None if has_cbu and has_ckd else ("CBU" if has_cbu else ("CKD" if has_ckd else None))
    return [
        {
            "name": "inspect_data_coverage",
            "arguments": {
                "country": args["country"],
                "powertrain": args["powertrain"],
                "import_mode": import_mode,
            },
        },
        {
            "name": "search_policy_rules",
            "arguments": {
                "country": args["country"],
                "powertrain": args["powertrain"],
                "keyword": "hybrid HEV PHEV EREV excise import duty FTA eligibility",
            },
        },
    ]



def _erev_architecture_prompt_if_needed(messages: list) -> str | None:
    text = _last_user_text(messages)
    lowered = text.lower()
    if not ("erev" in lowered or "增程" in text):
        return None
    direct_drive_markers = ("可直驱", "机械驱动", "机械连接", "发动机能驱动", "发动机参与驱动", "发动机驱动车轮", "汽油增程")
    series_only_markers = ("仅发电", "只发电", "纯串联", "车轮只由电机", "发动机不驱动")
    if any(m in text for m in direct_drive_markers) or any(m in text for m in series_only_markers):
        return None
    return (
        "这里不能只凭“EREV”和纯电续航来算最终马来西亚税号/消费税。"
        "马来西亚 8703.60 的关键是：车辆是否同时使用火花点火内燃机和电机推进，并且可外接充电；"
        "纯电续航 80km 或 200km 本身不是该组消费税分档条件。\n\n"
        "请先补充一个条件：这个 EREV 的发动机是否能通过机械连接参与驱动车轮？\n"
        "- 如果能，通常先按汽油 PHEV/8703.60 路径继续细分：车身类别 + 排量 + 两驱/四驱。\n"
        "- 如果发动机只发电、车轮只由电机驱动，不能自动套用 8703.60，建议作为独立归类风险并取得 JKDM 预裁定。\n\n"
        "目前系统不会再用“纯电续航200km”直接决定税率。"
    )

def _recover_implied_tool_calls(state: AgentState, messages: list, content: str) -> list[dict] | None:
    """Recover when the LLM promises tool use in prose but omits tool_call JSON."""
    if state.get("tool_call_count", 0):
        return None

    text = _last_user_text(messages)
    lowered_text = text.lower()
    lowered_content = content.lower()

    # Malaysia is the current default market for the calculator tools.  Accept
    # an omitted country as that default; only an explicitly different market
    # should prevent this recovery path.
    explicit_non_my = any(marker in lowered_text for marker in ("vietnam", "越南", "thailand", "泰国", "india", "印度"))
    if explicit_non_my and not ("malaysia" in lowered_text or "马来西亚" in text):
        return None

    promised_tool_use = (
        "调用工具" in content
        or "查询" in content
        or "检查数据" in content
        or "获取基础政策" in content
        or "tool" in lowered_content
        or "search" in lowered_content
        or "check" in lowered_content
    )
    explicit_tool_intent = (
        any(marker in text for marker in ("税", "关税", "消费税", "销售税", "综合税率", "税率"))
        or any(marker in lowered_text for marker in ("tax", "duty", "sales tax", "excise", "rate"))
    )
    if not promised_tool_use and not explicit_tool_intent:
        return None

    args = _infer_request_args(text)
    if _is_condition_question(text):
        return _condition_route_tool_calls(text)
    # Infer the requested route instead of requiring the old, overly narrow
    # “CBU + CKD + BEV comparison” shape.  A question such as “HEV CBU 的
    # 消费税是多少？” must execute calculate_cbu_tax immediately, even when
    # displacement/origin is still missing; the tool will return candidates
    # and an explicit missing-information list.
    has_cbu = "cbu" in lowered_text or "整车进口" in text or "整车" in text
    has_ckd = "ckd" in lowered_text or "散件" in text or "零件组装" in text
    if not has_cbu and not has_ckd:
        # Country-level automotive tax questions default to the CBU route,
        # matching the public assistant prompt and calculator default market.
        has_cbu = True

    calls: list[dict] = []
    if has_cbu and has_ckd:
        import_mode = None
    elif has_cbu:
        import_mode = "CBU"
    else:
        import_mode = "CKD"

    calls.append({
        "name": "inspect_data_coverage",
        "arguments": {
            "country": args["country"],
            "powertrain": args["powertrain"],
            "import_mode": import_mode,
        },
    })

    # Policy lookup is useful for tax/policy questions and gives the final
    # answer traceable rule evidence in addition to the numeric calculator.
    if any(marker in text for marker in ("税", "政策", "优惠", "关税", "消费税", "sales tax")) or any(
        marker in lowered_text for marker in ("tax", "policy", "duty", "rate")
    ):
        calls.append({
            "name": "search_policy_rules",
            "arguments": {
                "country": args["country"],
                "powertrain": args["powertrain"],
                "keyword": args["powertrain"],
            },
        })

    if has_cbu:
        calls.append({"name": "calculate_cbu_tax", "arguments": args})
    if has_ckd:
        calls.append({"name": "calculate_ckd_tax", "arguments": args})
    return calls


def _normalize_tool_calls_from_user(tool_calls: list[dict], messages: list) -> list[dict]:
    """Guardrail for model-generated tool args.

    The LLM may emit stale/partial arguments such as EREV with no displacement.
    For Malaysia CBU/CKD comparison tools, normalize from the latest user text so
    deterministic business logic wins over a malformed tool_call block.
    """
    text = _last_user_text(messages)
    lowered = text.lower()
    if not ("malaysia" in lowered or "马来西亚" in text):
        return tool_calls
    inferred = _infer_request_args(text)
    normalized: list[dict] = []
    for tc in tool_calls:
        name = tc.get("name", "")
        args = dict(tc.get("arguments", {}) or {})
        if name in {"calculate_cbu_tax", "calculate_ckd_tax"}:
            for key in ("country", "origin_country", "powertrain", "displacement_cc", "body_type", "drive_type", "effective_date"):
                value = inferred.get(key)
                if value is not None:
                    args[key] = value
        if name == "inspect_data_coverage":
            args["country"] = inferred.get("country", args.get("country", "MY"))
            args["powertrain"] = inferred.get("powertrain", args.get("powertrain"))
        normalized.append({"name": name, "arguments": args})
    return normalized


def _ensure_route_calculators(state: AgentState, messages: list, tool_calls: list[dict] | None) -> list[dict] | None:
    """Guarantee the calculator required by the user's explicit route.

    LLMs sometimes call ``search_policy_rules`` first and then stop with a
    prose answer.  That is useful for context but cannot answer a tax question.
    The route words in the user's message are deterministic business intent, so
    they must add the corresponding calculator regardless of model tool choice.
    """
    text = _last_user_text(messages)
    lowered = text.lower()
    explicit_non_my = any(marker in lowered for marker in ("vietnam", "越南", "thailand", "泰国", "india", "印度"))
    if explicit_non_my and not ("malaysia" in lowered or "马来西亚" in text):
        # The current calculator tools are Malaysia-specific. Never silently
        # turn a Vietnam/Thailand/India question into a Malaysia calculation.
        return tool_calls
    has_cbu = "cbu" in lowered or "整车进口" in text or "整车" in text
    has_ckd = "ckd" in lowered or "散件" in text or "零件组装" in text
    if not has_cbu and not has_ckd:
        vehicle_signal = any(
            marker in lowered or marker in text
            for marker in (
                "bev", "hev", "phev", "erev", "ice", "fcev", "纯电", "混动", "插混", "增程",
                "汽油", "柴油", "汽车", "车辆", "车型", "发动机",
            )
        )
        if not vehicle_signal:
            return None
        has_cbu = True

    calls = list(tool_calls or [])
    if _is_condition_question(text):
        # Conditions-only questions must never be upgraded to tax calculators,
        # even if the LLM happened to emit one alongside policy search.
        calls = [
            call for call in calls
            if str(call.get("name", "")) in {"inspect_data_coverage", "search_policy_rules"}
        ]
        if not calls:
            calls = _condition_route_tool_calls(text)
        return calls
    if not calls:
        explicit_tax_question = (
            any(marker in text for marker in ("税", "关税", "消费税", "销售税", "综合税率", "税率"))
            or any(marker in lowered for marker in ("tax", "duty", "sales tax", "excise", "rate"))
        )
        if not explicit_tax_question:
            return None
    existing_names = {str(item.get("name", "")) for item in calls if isinstance(item, dict)}
    inferred = _infer_request_args(text)
    if has_cbu and "calculate_cbu_tax" not in existing_names:
        calls.append({"name": "calculate_cbu_tax", "arguments": inferred})
    if has_ckd and "calculate_ckd_tax" not in existing_names:
        calls.append({"name": "calculate_ckd_tax", "arguments": inferred})
    return calls or None
def _tool_intro(tool_calls: list[dict]) -> str:
    return (
        "我先读取已有的CBU和CKD税负模型，再基于数据库结果给出比较结论。\n"
        "```tool_call\n"
        f"{json.dumps(tool_calls, ensure_ascii=False)}\n"
        "```"
    )


# ── Graph ───────────────────────────────────────────────────────────



def build_graph() -> StateGraph:
    llm = LLMProvider.create_model()

    def agent_node(state: AgentState) -> dict:
        step = state.get("step_count", 0)
        tool_count = state.get("tool_call_count", 0)

        if step >= MAX_STEPS or tool_count >= MAX_TOOLS:
            return {
                "messages": [AIMessage(content="已达到分析上限。请根据已有信息提出后续问题。")],
                "status": "done", "step_count": step + 1,
            }

        messages = _build_messages(state, step)
        force_final_answer = bool(state.get("force_final_answer", False))
        seeded_tool_calls = _seed_tool_calls(state, messages)
        if force_final_answer:
            # Do not seed or recover another tool round after results exist.
            # The model must now explain the actual returned data.
            seeded_tool_calls = None
            response = llm.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)
        elif seeded_tool_calls:
            content = _tool_intro(seeded_tool_calls)
        else:
            response = llm.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

        erev_prompt = _erev_architecture_prompt_if_needed(messages)
        if erev_prompt:
            content = erev_prompt

        # Check for tool calls. If the model says it will call/search tools but
        # forgets to emit the strict tool_call JSON block, recover deterministically
        # instead of returning a half-finished "I will query..." answer.
        tool_calls = None if force_final_answer else _parse_tool_calls(str(content))
        recovered_tool_calls = None
        if not force_final_answer and not tool_calls:
            recovered_tool_calls = _recover_implied_tool_calls(state, messages, str(content))
            if recovered_tool_calls:
                tool_calls = recovered_tool_calls
                content = _tool_intro(tool_calls)
        # A policy/coverage lookup alone is not sufficient for an explicit
        # CBU/CKD tax question. Add the route calculator before execution.
        tool_calls = None if force_final_answer else _ensure_route_calculators(state, messages, tool_calls)
        if tool_calls:
            tool_calls = _normalize_tool_calls_from_user(tool_calls, messages)
        has_tools = tool_calls is not None and len(tool_calls) > 0

        display = _clean_content(str(content))
        if force_final_answer:
            display = _apply_final_evidence_gate(
                display,
                state,
                _last_user_text(messages),
            )
        new_msg = AIMessage(content=display) if has_tools else AIMessage(content=display or str(content))

        new_messages = _history_messages(messages) + [new_msg]
        new_status = "calling_tools" if has_tools else "done"

        # If tool calls: execute them and append results as user-visible messages
        if has_tools:
            task_id = state.get("task_id", str(uuid.uuid4())[:12])
            signatures = list(state.get("executed_call_signatures", []))
            tool_results = dict(state.get("tool_results", {}))
            evidence_refs = list(state.get("evidence_refs", []))
            warnings = list(state.get("warnings", []))

            for tc in tool_calls:
                name = tc.get("name", "")
                args = tc.get("arguments", {})
                sig = f"{name}:{json.dumps(args, sort_keys=True)}"
                if sig in signatures:
                    continue
                signatures.append(sig)

                fn = TOOLS_BY_NAME.get(name)
                if fn is None:
                    new_messages.append(AIMessage(content=f"Unknown tool: {name}"))
                    warnings.append({"tool": name, "error": "unknown"})
                    continue

                try:
                    raw = fn.invoke(args)
                except Exception as exc:
                    new_messages.append(AIMessage(content=f"Tool {name} error: {exc}"))
                    warnings.append({"tool": name, "error": str(exc)})
                    continue

                if not isinstance(raw, dict):
                    raw = {"status": "ERROR", "error": "工具返回了非对象结果"}

                run_id = (raw or {}).get("_meta", {}).get("run_id", str(uuid.uuid4())[:8]) if raw else "?"
                fp = (raw or {}).get("_meta", {}).get("parameter_fingerprint", "") if raw else ""
                deps = (raw or {}).get("_meta", {}).get("depends_on_fields", []) if raw else []
                raw.pop("_meta", None) if raw and "_meta" in raw else None
                for ev in (raw or {}).get("evidence_refs", []):
                    if ev not in evidence_refs:
                        evidence_refs.append(ev)

                envelope = ToolResultEnvelope(
                    status="SUCCESS", tool_name=name, run_id=run_id, task_id=task_id,
                    parameter_fingerprint=fp, input_parameters=args, depends_on_fields=deps,
                    result=raw,
                    missing_information=(raw or {}).get("missing_information", []),
                    warnings=(raw or {}).get("warnings", []),
                    evidence_refs=(raw or {}).get("evidence_refs", []),
                )
                tool_results[run_id] = envelope.model_dump()

                # Every tool result carries an explicit provenance contract so
                # the synthesis round cannot mistake a web clue/candidate for
                # a verified tax result.
                new_messages.append(AIMessage(
                    content=_evidence_gated_tool_message(name, raw)
                ))

            plan = state.get("user_visible_plan", []) + [f"执行: {', '.join(t['name'] for t in tool_calls)}"]
            new_status = "reasoning"

            return {
                "messages": new_messages,
                "status": new_status,
                "step_count": step + 1,
                "tool_call_count": tool_count + len(tool_calls),
                "force_final_answer": True,
                "tool_results": tool_results,
                "executed_call_signatures": signatures,
                "evidence_refs": evidence_refs,
                "warnings": warnings,
                "user_visible_plan": plan,
            }

        return {
            "messages": new_messages,
            "status": new_status,
            "step_count": step + 1,
        }

    def route_after_agent(state: AgentState) -> Literal["agent", "__end__"]:
        status = state.get("status", "")
        step = state.get("step_count", 0)
        if status == "reasoning" and step < MAX_STEPS:
            return "agent"
        return "__end__"

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.set_entry_point("agent")
    builder.add_conditional_edges("agent", route_after_agent, {"agent": "agent", "__end__": END})

    return builder


_compiled_graph = None


def get_agent():
    global _compiled_graph
    if _compiled_graph is None:
        builder = build_graph()
        _compiled_graph = builder.compile(checkpointer=MemorySaver())
    return _compiled_graph
