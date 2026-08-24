"""Structured schemas for Agent decisions, tool results, and final answers.

Every LLM output is validated through these models — no natural-language parsing.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Union

from pydantic import BaseModel, Field


# ═════════════════════════════════════════════════════════════════════
#  Agent Decision Types
# ═════════════════════════════════════════════════════════════════════


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict


class CallToolAction(BaseModel):
    action: Literal["CALL_TOOL"] = "CALL_TOOL"
    tool_calls: list[ToolCallRequest]
    user_visible_plan: list[str] = Field(default_factory=list)


class AskUserAction(BaseModel):
    action: Literal["ASK_USER"] = "ASK_USER"
    question: str
    reason: str = ""
    expected_fields: list[str] = Field(default_factory=list)
    options: list[dict] = Field(default_factory=list)
    # Can carry a partial answer — enables "give results then ask" pattern
    partial_answer: "AgentAnswer | None" = None


class ContinueAction(BaseModel):
    action: Literal["CONTINUE"] = "CONTINUE"
    user_visible_plan: list[str] = Field(default_factory=list)


class FinalAnswerAction(BaseModel):
    action: Literal["FINAL_ANSWER"] = "FINAL_ANSWER"
    answer: "AgentAnswer"


AgentDecision = Union[CallToolAction, AskUserAction, ContinueAction, FinalAnswerAction]


# ═════════════════════════════════════════════════════════════════════
#  Evidence + Calculation Items (linked by ID)
# ═════════════════════════════════════════════════════════════════════


class EvidenceRefItem(BaseModel):
    evidence_id: str
    source_type: Literal["OFFICIAL_POLICY", "DATABASE_RECORD", "SYSTEM_DIAGNOSTIC"] = "OFFICIAL_POLICY"
    document_title: str = ""
    authority_name: str = ""
    locator: str = ""           # formatted locator_value
    official_url: str | None = None
    clause_id: str | None = None


class FactItem(BaseModel):
    fact_id: str
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_type: Literal["OFFICIAL_POLICY", "DATABASE_RECORD", "SYSTEM_DIAGNOSTIC"] = "OFFICIAL_POLICY"


class CalculationItem(BaseModel):
    calculation_id: str
    label: str
    value: str
    tool_run_id: str
    evidence_ids: list[str] = Field(default_factory=list)


# ═════════════════════════════════════════════════════════════════════
#  Final Answer
# ═════════════════════════════════════════════════════════════════════


AnswerStatus = Literal[
    "FINAL",                # complete conclusion
    "PARTIAL",              # partial, some info missing
    "WAITING_FOR_USER",     # waiting for user
    "INSUFFICIENT_DATA",    # data insufficient to judge
    "CONFLICTING_DATA",     # tool results conflicting
    "TOOL_ERROR",           # tool execution failed
]


class AgentAnswer(BaseModel):
    status: AnswerStatus
    headline: str = ""
    facts: list[FactItem] = Field(default_factory=list)
    calculations: list[CalculationItem] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRefItem] = Field(default_factory=list)
    narrative: str = ""


# ═════════════════════════════════════════════════════════════════════
#  Tool Result Envelope
# ═════════════════════════════════════════════════════════════════════


ToolStatus = Literal["SUCCESS", "PARTIAL", "NO_DATA", "ERROR"]


class ToolResultEnvelope(BaseModel):
    status: ToolStatus
    tool_name: str
    run_id: str
    task_id: str
    parameter_fingerprint: str
    input_parameters: dict = Field(default_factory=dict)
    depends_on_fields: list[str] = Field(default_factory=list)
    data_version: str | None = None
    result: dict | None = None
    missing_information: list[str] = Field(default_factory=list)
    warnings: list[dict] = Field(default_factory=list)
    evidence_refs: list[EvidenceRefItem] = Field(default_factory=list)


# ═════════════════════════════════════════════════════════════════════
#  SSE Event Schemas
# ═════════════════════════════════════════════════════════════════════


class SSEStatusEvent(BaseModel):
    event: Literal["status"] = "status"
    data: dict


class SSERequestIdEvent(BaseModel):
    event: Literal["request_id"] = "request_id"
    data: dict


class SSEPlanUpdatedEvent(BaseModel):
    event: Literal["plan_updated"] = "plan_updated"
    data: dict  # {plan: [...]}


class SSEContextUpdatedEvent(BaseModel):
    event: Literal["context_updated"] = "context_updated"
    data: dict  # {confirmed: {...}, tentative: {...}, context_revision: ...}


class SSEToolStartedEvent(BaseModel):
    event: Literal["tool_started"] = "tool_started"
    data: dict  # {tool_name, args}


class SSEToolCompletedEvent(BaseModel):
    event: Literal["tool_completed"] = "tool_completed"
    data: dict  # {tool_name, summary}


class SSEToolFailedEvent(BaseModel):
    event: Literal["tool_failed"] = "tool_failed"
    data: dict  # {tool_name, error}


class SSEAskUserEvent(BaseModel):
    event: Literal["ask_user"] = "ask_user"
    data: dict  # {question, reason, options, partial_answer?}


class SSEAnswerDeltaEvent(BaseModel):
    event: Literal["answer_delta"] = "answer_delta"
    data: dict  # {text}


class SSEAnswerCompletedEvent(BaseModel):
    event: Literal["answer_completed"] = "answer_completed"
    data: AgentAnswer


class SSECancelledEvent(BaseModel):
    event: Literal["cancelled"] = "cancelled"
    data: dict = Field(default_factory=dict)


class SSEErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    data: dict  # {message}


# ═════════════════════════════════════════════════════════════════════
#  Public Workspace State (safe subset for frontend)
# ═════════════════════════════════════════════════════════════════════


class PublicWorkspaceState(BaseModel):
    conversation_id: str = ""
    user_goal: str | None = None
    confirmed_context: dict = Field(default_factory=dict)
    pending_context: list[dict] = Field(default_factory=list)
    user_visible_plan: list[str] = Field(default_factory=list)
    calculations: list[CalculationItem] = Field(default_factory=list)
    evidence_refs: list[EvidenceRefItem] = Field(default_factory=list)
    status: str = ""
