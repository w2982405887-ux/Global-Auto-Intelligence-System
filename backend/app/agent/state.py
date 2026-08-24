"""AgentState — collaboration-oriented state for LangGraph Co-work Agent.

Key design decisions:
  - confirmed_context != tentative_context (Agent must not guess)
  - Each ToolResultEnvelope records depends_on_fields for auto-invalidation
  - pending_interrupt preserves the ASK_USER state for resume
  - task_id lifecycle: new goal → new ID; user reply to ASK_USER → keep ID;
    user corrects a condition → keep ID but invalidate dependent results
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # ── 会话 ──
    messages: list     # LangGraph add_messages reducer
    conversation_id: str

    # ── 用户目标 ──
    user_goal: str | None

    # ── 已确认的事实 ──
    confirmed_context: dict          # {powertrain: "BEV", origin_country: "CN", ...}
    context_revision: int            # increment on each confirmed_context change

    # ── Agent 推测但未经用户确认 ──
    tentative_context: dict          # {powertrain: {value: "BEV", confidence: 0.45}}

    # ── 缺失信息 ──
    missing_information: list[dict]

    # ── 用户可见行动计划 — 只能展示行动，不能展示内部推理 ──
    user_visible_plan: list[str]

    # ── 工具调用 ──
    tool_history: list[dict]
    tool_results: dict               # keyed by run_id
    executed_call_signatures: list[str]  # list→set for dedup; compatible w/ checkpoint serialization
    invalidated_result_ids: list[str]    # results that were invalidated by context revision

    # ── 依据与风险 ──
    evidence_refs: list[dict]
    warnings: list[dict]

    # ── 循环控制 ──
    step_count: int
    tool_call_count: int
    consecutive_continue_count: int   # max 2

    # ── 任务 ──
    task_id: str

    # ── 上下文控制 ──
    conversation_summary: str | None
    active_task_message_ids: list[str]
    context_token_budget: int

    # ── 中断恢复 ──
    pending_interrupt: dict | None   # {interrupt_id, task_id, expected_fields, question, created_at}

    # ── 状态 ──
    status: str   # "reasoning" | "calling_tools" | "asking_user" | "done" | "error"
    # After a tool round, the next model round must synthesize an answer from
    # the returned data instead of emitting another tool request.
    force_final_answer: bool
