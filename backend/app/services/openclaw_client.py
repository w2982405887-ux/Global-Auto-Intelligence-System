"""Controlled OpenClaw Gateway adapter.

The browser never receives the OpenClaw token.  FastAPI calls the Gateway's
OpenAI-compatible HTTP surface and executes only the explicitly allowlisted
business tools when OpenClaw returns a client-side function call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import AsyncGenerator
from typing import Any, Callable
from urllib.parse import urljoin

import httpx

from app.agent.tools.cbu_tool import calculate_cbu_tax
from app.agent.tools.ckd_tool import calculate_ckd_tax
from app.agent.tools.coverage_tool import inspect_data_coverage
from app.agent.tools.evidence_tool import get_policy_evidence
from app.agent.tools.policy_tool import search_policy_rules
from app.core.config import Settings


_OPENCLAW_EVIDENCE_GATE_MARKER = "[AUTOPOLICY_EVIDENCE_GATE_V1]"
_EXTERNAL_SEARCH_TOOL_NAMES = {"gais_web_search", "web_search", "openai_web_search"}
_OPENCLAW_EVIDENCE_GATE_PROMPT = f"""
{_OPENCLAW_EVIDENCE_GATE_MARKER}
Answering safety contract for AutoPolicy:
- A deterministic tax rate may be stated as confirmed only when the internal
  calculator result is complete and marked VERIFIED/statutory-chain-complete
  for the requested country, date, route, powertrain, and classification.
- gais_web_search and other web results are discovery/corroboration only. They
  never override or complete internal data and cannot turn a search snippet
  into a definite rate.
- Candidate HS codes, candidate regimes, and lowest FTA rates are conditional;
  say 候选/条件性. Keep 未入库, 未匹配, 待归类, and 不适用 distinct.
- Keep MFN/FTA statutory rates separate from conditional incentives such as
  Vietnam 98.49. A 0% import-duty line is not a 0% comprehensive tax burden.
- For an explicit rate question with complete MFN/ACFTA/RCEP rows, answer each
  regime separately and bind it to the tool evidence/source. If incomplete,
  state exactly what is missing and do not fill it from web results.
- Never expose tool-call JSON or an intermediate tool-round draft to the user.
""".strip()


def _prepare_request_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add the evidence contract once without mutating caller-owned history."""

    prepared = [dict(message) for message in messages]
    if any(
        str(message.get("content") or "").find(_OPENCLAW_EVIDENCE_GATE_MARKER) >= 0
        for message in prepared
        if message.get("role") == "system"
    ):
        return prepared
    system_index = next(
        (index for index, message in enumerate(prepared) if message.get("role") == "system"),
        -1,
    )
    insert_at = system_index + 1 if system_index >= 0 else 0
    prepared.insert(insert_at, {"role": "system", "content": _OPENCLAW_EVIDENCE_GATE_PROMPT})
    return prepared


def _openclaw_last_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                str(part.get("text") or "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
    return ""


def _openclaw_is_rate_question(text: str) -> bool:
    lowered = text.lower()
    condition_only = any(
        marker in text or marker in lowered
        for marker in ("影响条件", "影响因素", "需要哪些条件", "不是具体税率", "what conditions", "eligibility")
    )
    if condition_only:
        return False
    return any(
        marker in text or marker in lowered
        for marker in ("税率", "税负", "关税", "综合税率", "税额", "多少", "tax", "duty", "rate")
    )


def _openclaw_calculator_complete(name: str, result: dict[str, Any]) -> tuple[str, bool]:
    if name not in {"calculate_cbu_tax", "calculate_ckd_tax"}:
        return "NONE", False
    if str(result.get("applicability_status") or "").upper() in {
        "UNSUPPORTED_COUNTRY", "CLASSIFICATION_SELECTION_REQUIRED", "CANDIDATE_REGIMES",
    }:
        return "NONE", False
    if result.get("is_complete_statutory_chain") is True:
        return "FULL_CHAIN", True
    combined = result.get("combined_results")
    if isinstance(combined, list) and any(
        isinstance(item, dict)
        and item.get("is_complete") is True
        and item.get("effective_tax_rate") is not None
        for item in combined
    ):
        return "FULL_CHAIN", True
    for path in result.get("paths") or []:
        if isinstance(path, dict) and (path.get("statutory") or {}).get("is_complete_statutory_chain") is True:
            return "FULL_CHAIN", True
    import_stage = result.get("import_stage") or {}
    rows = import_stage.get("import_effective_rates")
    if name == "calculate_ckd_tax" and isinstance(rows, list) and any(
        isinstance(row, dict) and row.get("import_effective_rate") is not None for row in rows
    ) and result.get("full_cycle_available") is not True:
        return "IMPORT_STAGE", True
    return "NONE", False


def _openclaw_semantic_status(name: str, result: dict[str, Any]) -> str:
    raw = str(result.get("applicability_status") or result.get("status") or "").upper()
    if raw in {"UNSUPPORTED_COUNTRY", "NOT_APPLICABLE", "INAPPLICABLE"}:
        return "NOT_APPLICABLE"
    if raw in {"CLASSIFICATION_SELECTION_REQUIRED", "SCENARIO_MATCHED_CLASSIFICATION_PENDING"}:
        return "PENDING_CLASSIFICATION"
    if raw in {"CANDIDATE_REGIMES", "CANDIDATE", "CANDIDATES"}:
        return "CANDIDATE_CONDITIONAL"
    if raw in {"NOT_FOUND", "NO_DATA", "NOT_IN_DATABASE"}:
        return "NOT_IN_DATABASE"
    if name in _EXTERNAL_SEARCH_TOOL_NAMES:
        return "SEARCH_ONLY"
    if name == "search_policy_rules":
        return "VERIFIED_POLICY" if int(result.get("total") or 0) > 0 else "NOT_MATCHED"
    if name == "get_policy_evidence":
        return "OFFICIAL_EVIDENCE" if result.get("status") == "FOUND" else "NOT_IN_DATABASE"
    return "VERIFIED_RESULT" if _openclaw_calculator_complete(name, result)[1] else "NOT_MATCHED"


def _openclaw_evidence_gate(name: str, result: Any) -> dict[str, Any]:
    payload = result if isinstance(result, dict) else {"value": result}
    semantic = _openclaw_semantic_status(name, payload)
    scope, complete = _openclaw_calculator_complete(name, payload)
    if name in _EXTERNAL_SEARCH_TOOL_NAMES:
        tier = "EXTERNAL_UNVERIFIED"
    elif name == "search_policy_rules":
        tier = "INTERNAL_VERIFIED_POLICY" if semantic == "VERIFIED_POLICY" else "INTERNAL_NO_MATCH"
    elif complete:
        tier = "INTERNAL_VERIFIED"
    elif name == "get_policy_evidence":
        tier = "OFFICIAL_EVIDENCE" if semantic == "OFFICIAL_EVIDENCE" else "INTERNAL_NO_MATCH"
    else:
        tier = "INTERNAL_INCOMPLETE"
    text = json.dumps(payload, ensure_ascii=False)
    return {
        "semantic_status": semantic,
        "source_tier": tier,
        "scope": scope,
        "can_confirm_numeric_rates": bool(tier == "INTERNAL_VERIFIED"),
        "candidate_only": semantic in {"CANDIDATE_CONDITIONAL", "PENDING_CLASSIFICATION"},
        "web_search_may_override": False,
        "zero_rate_is_not_total_burden": ("零关税" in text or '"rate": "0' in text or '"rate": 0' in text),
    }


def _openclaw_tool_payload(name: str, result: dict[str, Any]) -> str:
    gate = _openclaw_evidence_gate(name, result)
    return json.dumps(
        {"tool_name": name, "evidence_gate": gate, "tool_result": result},
        ensure_ascii=False,
        default=str,
    )[:120_000]


def _openclaw_apply_final_gate(content: str, messages: list[dict[str, Any]]) -> str:
    """Add a visible limitation when no verified calculator result exists."""

    user_text = _openclaw_last_user_text(messages)
    if not _openclaw_is_rate_question(user_text):
        return content
    verified = False
    for message in messages:
        if message.get("role") != "tool":
            continue
        try:
            payload = json.loads(str(message.get("content") or "{}"))
        except (TypeError, ValueError):
            continue
        result = payload.get("tool_result") if isinstance(payload, dict) else None
        name = ""
        if isinstance(result, dict):
            # Tool messages do not carry the name in the OpenAI protocol, so
            # inspect the wrapper inserted by this adapter when available.
            name = str(payload.get("tool_name") or "")
        if name and isinstance(result, dict) and _openclaw_evidence_gate(name, result).get("can_confirm_numeric_rates"):
            verified = True
    guarded = content.strip()
    if not verified and not guarded.startswith("⚠️ 证据门禁"):
        guarded = (
            "⚠️ 证据门禁：内部计算器未返回完整、已核验的确定税率。"
            "搜索结果或候选税号只能作为线索，不能替代内部税率数据。\n\n" + guarded
        )
    if ("0%" in guarded or "零关税" in guarded or "0％" in guarded) and "不等于综合税负" not in guarded:
        guarded += "\n\n注：0%仅指对应进口税行（且须满足条件），不等于综合税负为0%，也不等于整车或全流程税负为0%。"
    return guarded


class OpenClawError(RuntimeError):
    """Base class for adapter failures safe to expose as a 502/503."""


class OpenClawNotConfigured(OpenClawError):
    """OpenClaw is disabled or has no gateway token."""


class OpenClawUnavailable(OpenClawError):
    """The Gateway could not be reached or returned an invalid response."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[[dict[str, Any]], Any]
    parameters: dict[str, Any]


@dataclass(frozen=True)
class OpenClawChatResult:
    content: str
    tool_events: list[dict[str, Any]]
    usage: dict[str, Any] | None = None
    rounds: int = 0


@dataclass(frozen=True)
class OpenClawStreamEvent:
    """One auditable event emitted while a Gateway turn is running.

    ``event`` names intentionally mirror the assistant SSE contract. Keeping
    this adapter-level type means the router does not need to understand
    OpenAI delta/tool-call wire details, while the non-streaming ``chat`` API
    remains available to callers that need a single JSON response.
    """

    event: str
    data: dict[str, Any]


def _schema_for(tool: Any) -> dict[str, Any]:
    schema_model = getattr(tool, "args_schema", None)
    if schema_model is not None and hasattr(schema_model, "model_json_schema"):
        schema = schema_model.model_json_schema()
        # OpenAI function schemas only need a JSON Schema object here.  Pydantic
        # metadata is harmless, but removing title keeps prompts smaller.
        schema.pop("title", None)
        return schema
    return {"type": "object", "additionalProperties": True}


def _invoke_langchain_tool(tool: Any, args: dict[str, Any]) -> Any:
    """Invoke a synchronous LangChain StructuredTool without exposing internals."""

    invoke = getattr(tool, "invoke", None)
    if invoke is None:
        raise OpenClawError(f"Tool {tool!r} is not invokable")
    return invoke(args)


def _tool_specs() -> dict[str, ToolSpec]:
    return {
        "calculate_cbu_tax": ToolSpec(
            name="calculate_cbu_tax",
            description=(
                "Calculate a configured-country CBU passenger-car import tax scenario (currently MY or VN). "
                "Pass the user's destination as ISO2 in country; never substitute MY for another country. "
                "Use only when the user asks for a deterministic tax calculation."
            ),
            handler=lambda args: _invoke_langchain_tool(calculate_cbu_tax, args),
            parameters=_schema_for(calculate_cbu_tax),
        ),
        "calculate_ckd_tax": ToolSpec(
            name="calculate_ckd_tax",
            description=(
                "Calculate a configured-country CKD import and local-assembly tax scenario (currently MY or VN). "
                "For VN, use component candidates and explicit confirmed component codes (for example "
                "VN-CKD-TRACTION-BATTERY); component_code may filter a focused question, and the tool never auto-selects the lowest rate. "
                "Pass the user's destination as ISO2 in country and never substitute MY for another country."
            ),
            handler=lambda args: _invoke_langchain_tool(calculate_ckd_tax, args),
            parameters=_schema_for(calculate_ckd_tax),
        ),
        "search_policy_rules": ToolSpec(
            name="search_policy_rules",
            description=(
                "Search verified automotive policy rules and FTA conditions in the database. "
                "Supports configured markets such as MY and VN; pass country as ISO2 from the user request. "
                "Return evidence references and effective dates; never invent a rate or cross-country fallback."
            ),
            handler=lambda args: _invoke_langchain_tool(search_policy_rules, args),
            parameters=_schema_for(search_policy_rules),
        ),
        "get_policy_evidence": ToolSpec(
            name="get_policy_evidence",
            description="Retrieve the original clause, Chinese translation, and official URL for a clause id.",
            handler=lambda args: _invoke_langchain_tool(get_policy_evidence, args),
            parameters=_schema_for(get_policy_evidence),
        ),
        "inspect_data_coverage": ToolSpec(
            name="inspect_data_coverage",
            description=(
                "Inspect database coverage and explain why a requested country/powertrain/route "
                "cannot be calculated. Preserve the requested country and never assume Malaysia."
            ),
            handler=lambda args: _invoke_langchain_tool(inspect_data_coverage, args),
            parameters=_schema_for(inspect_data_coverage),
        ),
    }


def _openai_tools(specs: dict[str, ToolSpec] | None = None) -> list[dict[str, Any]]:
    specs = specs or _tool_specs()
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }
        for spec in specs.values()
    ]


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(str(item.get("text", "")))
        return " ".join(texts)
    return str(content or "")


def _tool_signature(name: str, args: Any) -> str:
    """Return a stable audit/deduplication key for one tool invocation."""

    return f"{name}:{json.dumps(args, ensure_ascii=False, sort_keys=True, default=str)}"


def _tool_audit(
    *,
    round_number: int,
    name: str,
    args: Any,
    signature: str | None,
    duplicate_blocked: bool = False,
) -> dict[str, Any]:
    """Common, JSON-safe fields attached to every streamed tool event.

    The UI and history layer need to distinguish a legitimate refinement call
    from an exact duplicate.  Keeping the normalized arguments and stable
    signature on the event also makes the tool loop auditable without exposing
    the model's hidden draft text.
    """

    return {
        "round": round_number,
        "name": name,
        "tool_name": name,
        "args": args,
        "signature": signature,
        "duplicate_blocked": duplicate_blocked,
    }


class OpenClawClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.specs = _tool_specs()
        # The Gateway's own web tool is optional and provider-specific.  Keep a
        # backend-owned search function in the caller-supplied allowlist so the
        # model can still search through a controlled, auditable path when the
        # Gateway has no search credential yet.
        self.specs["gais_web_search"] = ToolSpec(
            name="gais_web_search",
            description=(
                "Search current public web information through the configured backend provider. "
                "Use for policy/news questions only; when country is supplied, include it in the search context. "
                "Cite returned URLs and never invent results."
            ),
            handler=lambda args: _web_search(self.settings, args),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A focused web search query."},
                    "count": {"type": "integer", "minimum": 1, "maximum": 10},
                    "country": {"type": "string", "description": "Optional ISO country code."},
                    "freshness": {"type": "string", "description": "Optional Brave freshness filter."},
                    "search_depth": {"type": "string", "enum": ["basic", "advanced"], "description": "Tavily search depth."},
                    "topic": {"type": "string", "enum": ["general", "news", "finance"], "description": "Tavily topic."},
                    "time_range": {"type": "string", "description": "Tavily time range such as week, month, or year."},
                    "include_domains": {"type": "array", "items": {"type": "string"}, "maxItems": 20, "description": "Optional domains to restrict the search."},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        )

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.openclaw_enabled
            and self.settings.openclaw_base_url
            and self.settings.openclaw_gateway_token
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.openclaw_gateway_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "DISABLED", "configured": False}
        url = self.settings.openclaw_base_url.rstrip("/") + "/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._headers())
            if response.status_code >= 400:
                return {"status": "ERROR", "configured": True, "http_status": response.status_code}
            payload = response.json()
            return {"status": "OK", "configured": True, "models": payload.get("data", [])}
        except (httpx.HTTPError, ValueError) as exc:
            return {"status": "UNAVAILABLE", "configured": True, "error": str(exc)}

    async def chat(
        self,
        *,
        conversation_id: str,
        messages: list[dict[str, Any]],
    ) -> OpenClawChatResult:
        if not self.enabled:
            raise OpenClawNotConfigured(
                "OpenClaw 未启用或缺少 GAIS_OPENCLAW_GATEWAY_TOKEN。"
            )

        request_messages = _prepare_request_messages(messages)
        tools = _openai_tools(self.specs)
        tool_events: list[dict[str, Any]] = []
        seen_call_signatures: set[str] = set()
        total_tool_calls = 0
        usage: dict[str, Any] | None = None
        max_rounds = max(1, min(self.settings.openclaw_max_tool_rounds, 12))
        url = self.settings.openclaw_base_url.rstrip("/") + "/v1/chat/completions"

        async with httpx.AsyncClient(timeout=self.settings.openclaw_timeout_seconds) as client:
            for round_index in range(max_rounds):
                body: dict[str, Any] = {
                    "model": self.settings.openclaw_model,
                    "user": f"conv:{conversation_id}",
                    "messages": request_messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": False,
                }
                headers = self._headers()
                if self.settings.openclaw_upstream_model:
                    headers["x-openclaw-model"] = self.settings.openclaw_upstream_model

                try:
                    response = await client.post(url, headers=headers, json=body)
                except httpx.HTTPError as exc:
                    raise OpenClawUnavailable(f"OpenClaw Gateway 请求失败：{exc}") from exc

                if response.status_code >= 400:
                    detail = response.text[:500]
                    raise OpenClawUnavailable(
                        f"OpenClaw Gateway 返回 HTTP {response.status_code}: {detail}"
                    )
                try:
                    payload = response.json()
                    choice = payload["choices"][0]
                    message = choice.get("message") or {}
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    raise OpenClawUnavailable("OpenClaw 返回了无法解析的响应") from exc

                usage = payload.get("usage") or usage
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    content = _content_to_text(message.get("content"))
                    if content.strip():
                        return OpenClawChatResult(
                            content=_openclaw_apply_final_gate(content, request_messages),
                            tool_events=tool_events,
                            usage=usage,
                            rounds=round_index + 1,
                        )
                    return OpenClawChatResult(
                        content="OpenClaw 已完成处理，但没有返回可显示的文本。",
                        tool_events=tool_events,
                        usage=usage,
                        rounds=round_index + 1,
                    )

                # The follow-up request must replay the assistant tool-call
                # message exactly enough for OpenClaw to bind tool_call_id.
                request_messages.append(
                    {
                        "role": "assistant",
                        "content": message.get("content") or "",
                        "tool_calls": tool_calls,
                    }
                )
                for call in tool_calls:
                    total_tool_calls += 1
                    function = call.get("function") or {}
                    name = str(function.get("name") or "")
                    call_id = str(call.get("id") or f"call-{round_index}")
                    raw_args = function.get("arguments") or "{}"
                    args: dict[str, Any] | None = None
                    signature: str | None = None
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        if not isinstance(args, dict):
                            raise ValueError("tool arguments must be an object")
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        result: dict[str, Any] = {
                            "status": "ERROR",
                            "error": f"工具参数不是有效 JSON：{exc}",
                        }
                        audit = _tool_audit(
                            round_number=round_index + 1,
                            name=name,
                            args=None,
                            signature=None,
                        )
                        audit["raw_args"] = raw_args
                        tool_events.append({**audit, "status": "error", "summary": result["error"]})
                    else:
                        signature = _tool_signature(name, args)
                        audit = _tool_audit(
                            round_number=round_index + 1,
                            name=name,
                            args=args,
                            signature=signature,
                        )
                        audit["raw_args"] = raw_args
                        if total_tool_calls > max_rounds * 4:
                            result = {"status": "ERROR", "error": "工具调用总数达到安全上限"}
                            tool_events.append({**audit, "status": "error", "summary": result["error"]})
                        elif signature in seen_call_signatures:
                            result = {"status": "ERROR", "error": "检测到重复工具调用，已阻止重复执行"}
                            audit["duplicate_blocked"] = True
                            tool_events.append({**audit, "status": "error", "summary": result["error"]})
                        elif name not in self.specs:
                            result = {"status": "ERROR", "error": f"工具未被允许：{name}"}
                            tool_events.append({**audit, "status": "error", "summary": result["error"]})
                        else:
                            seen_call_signatures.add(signature)
                            try:
                                result = self.specs[name].handler(args)
                                tool_events.append({
                                    **audit,
                                    "status": "done",
                                    "summary": _tool_summary(name, result),
                                })
                            except Exception as exc:  # tool errors must return to the model
                                result = {"status": "ERROR", "error": f"工具执行失败：{exc}"}
                                tool_events.append({**audit, "status": "error", "summary": result["error"]})

                    request_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": _openclaw_tool_payload(name, result),
                        }
                    )

        return OpenClawChatResult(
            content=(
                "工具分析已达到安全轮次上限，未取得最终模型结论；"
                "系统未将工具轮中的草稿作为结论。请查看工具审计并补充缺失条件后重试。"
            ),
            tool_events=tool_events,
            usage=usage,
            rounds=max_rounds,
        )

    async def chat_stream(
        self,
        *,
        conversation_id: str,
        messages: list[dict[str, Any]],
    ) -> AsyncGenerator[OpenClawStreamEvent, None]:
        """Stream one OpenClaw turn while preserving the allowlisted tool loop.

        OpenClaw exposes an OpenAI-compatible streaming endpoint.  Each model
        round is streamed to the caller, while a tool-call round is completed
        locally before the next model round starts.  Tool calls are assembled
        from fragmented ``delta.tool_calls`` records and replayed with their
        original IDs, so streaming does not weaken the existing tool safety
        checks or change the non-streaming ``chat`` contract.
        """

        if not self.enabled:
            raise OpenClawNotConfigured(
                "OpenClaw 未启用或缺少 GAIS_OPENCLAW_GATEWAY_TOKEN。"
            )

        request_messages = _prepare_request_messages(messages)
        tools = _openai_tools(self.specs)
        tool_events: list[dict[str, Any]] = []
        seen_call_signatures: set[str] = set()
        total_tool_calls = 0
        usage: dict[str, Any] | None = None
        max_rounds = max(1, min(self.settings.openclaw_max_tool_rounds, 12))
        url = self.settings.openclaw_base_url.rstrip("/") + "/v1/chat/completions"
        visible_content = ""

        async with httpx.AsyncClient(timeout=self.settings.openclaw_timeout_seconds) as client:
            for round_index in range(max_rounds):
                yield OpenClawStreamEvent(
                    "status",
                    {
                        "status": "reasoning" if round_index == 0 else "synthesizing",
                        "round": round_index + 1,
                    },
                )
                body: dict[str, Any] = {
                    "model": self.settings.openclaw_model,
                    "user": f"conv:{conversation_id}",
                    "messages": request_messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": True,
                }
                headers = self._headers()
                headers["Accept"] = "text/event-stream, application/json"
                if self.settings.openclaw_upstream_model:
                    headers["x-openclaw-model"] = self.settings.openclaw_upstream_model

                # A model may emit a plausible-looking explanation before it
                # decides to call a tool.  Buffer the whole round until the
                # Gateway response is complete; only a round with no tool
                # calls is allowed to become visible answer text.
                round_content_parts: list[str] = []
                tool_buffers: dict[int, dict[str, Any]] = {}
                last_message: dict[str, Any] = {}
                saw_payload = False
                saw_delta_content = False
                emitted_fallback_message = False

                try:
                    async with client.stream("POST", url, headers=headers, json=body) as response:
                        if response.status_code >= 400:
                            detail = (await response.aread()).decode("utf-8", errors="replace")[:500]
                            raise OpenClawUnavailable(
                                f"OpenClaw Gateway 返回 HTTP {response.status_code}: {detail}"
                            )
                        async for line in response.aiter_lines():
                            raw_line = line.strip()
                            if not raw_line or raw_line.startswith(":"):
                                continue
                            if raw_line.startswith("data:"):
                                raw_line = raw_line[5:].strip()
                            if raw_line == "[DONE]":
                                continue
                            try:
                                payload = json.loads(raw_line)
                            except (TypeError, ValueError):
                                # A Gateway may split a JSON object across
                                # transport lines; ignore keepalive fragments
                                # and let the missing-payload guard below give
                                # the caller a useful error if nothing parsed.
                                continue
                            if not isinstance(payload, dict):
                                continue
                            saw_payload = True
                            usage = payload.get("usage") or usage
                            choices = payload.get("choices") or []
                            if not choices:
                                continue
                            choice = choices[0] or {}
                            delta = choice.get("delta") or {}
                            message = choice.get("message") or {}
                            if isinstance(message, dict) and message:
                                last_message = message

                            delta_piece = _content_to_text(delta.get("content"))
                            piece = delta_piece
                            if not piece and not saw_delta_content and not emitted_fallback_message and isinstance(message, dict):
                                # Handles gateways that ignore stream=true and
                                # return one ordinary Chat Completions object.
                                piece = _content_to_text(message.get("content"))
                                emitted_fallback_message = bool(piece)
                            if delta_piece:
                                saw_delta_content = True
                            # Standard streaming deltas are ordered fragments;
                            # repeated text is valid and must never be treated
                            # as a duplicate.
                            if piece:
                                round_content_parts.append(piece)

                            delta_tool_calls = delta.get("tool_calls") or []
                            if not delta_tool_calls and isinstance(message, dict):
                                delta_tool_calls = message.get("tool_calls") or []
                            for part_index, part in enumerate(delta_tool_calls):
                                if not isinstance(part, dict):
                                    continue
                                index = int(part.get("index", part_index))
                                current = tool_buffers.setdefault(
                                    index,
                                    {
                                        "id": str(part.get("id") or f"call-{round_index}-{index}"),
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""},
                                    },
                                )
                                if part.get("id"):
                                    current["id"] = str(part["id"])
                                function = part.get("function") or {}
                                target = current["function"]
                                if function.get("name"):
                                    target["name"] += str(function["name"])
                                if function.get("arguments"):
                                    target["arguments"] += str(function["arguments"])
                except httpx.HTTPError as exc:
                    raise OpenClawUnavailable(f"OpenClaw Gateway 请求失败：{exc}") from exc

                if not saw_payload:
                    raise OpenClawUnavailable("OpenClaw 返回了无法解析的流式响应")

                tool_calls = [tool_buffers[index] for index in sorted(tool_buffers)]
                if not tool_calls:
                    # This is the first point at which we know that the round
                    # is the final answer round.  Emit its buffered pieces now
                    # so the client still receives answer_delta events without
                    # ever seeing an ungrounded tool-round draft.
                    round_content = "".join(round_content_parts)
                    if not round_content.strip():
                        round_content = "OpenClaw 已完成处理，但没有返回可显示的文本。"
                        round_content_parts = [round_content]
                    visible_content = _openclaw_apply_final_gate(round_content, request_messages)
                    # Preserve the gateway's original token/chunk boundaries
                    # when the gate does not change the answer.  If it adds a
                    # warning or caveat, emit the gated answer as one buffered
                    # event so the client never sees an ungrounded numeric
                    # claim before the warning.
                    if visible_content != round_content:
                        round_content_parts = [visible_content]
                    for piece in round_content_parts:
                        if piece:
                            yield OpenClawStreamEvent("answer_delta", {"text": piece})
                    yield OpenClawStreamEvent(
                        "answer_completed",
                        {
                            "status": "FINAL",
                            "narrative": visible_content,
                            "tool_calls": tool_events,
                            "usage": usage,
                            "rounds": round_index + 1,
                        },
                    )
                    return

                # The follow-up request must replay the assistant tool-call
                # message exactly enough for OpenClaw to bind tool_call_id.
                request_messages.append(
                    {
                        "role": "assistant",
                        # The model must receive its draft when replaying the
                        # assistant tool-call message, but it is intentionally
                        # never emitted as answer_delta to the user.
                        "content": "".join(round_content_parts) or last_message.get("content") or "",
                        "tool_calls": tool_calls,
                    }
                )
                for call in tool_calls:
                    total_tool_calls += 1
                    function = call.get("function") or {}
                    name = str(function.get("name") or "")
                    call_id = str(call.get("id") or f"call-{round_index}")
                    raw_args = function.get("arguments") or "{}"
                    args: dict[str, Any] | None = None
                    signature: str | None = None
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        if not isinstance(args, dict):
                            raise ValueError("tool arguments must be an object")
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        result: dict[str, Any] = {
                            "status": "ERROR",
                            "error": f"工具参数不是有效 JSON：{exc}",
                        }
                        audit = _tool_audit(
                            round_number=round_index + 1,
                            name=name,
                            args=None,
                            signature=None,
                        )
                        audit["raw_args"] = raw_args
                        yield OpenClawStreamEvent("tool_started", {**audit, "status": "started"})
                        tool_events.append({**audit, "status": "error", "summary": result["error"]})
                        yield OpenClawStreamEvent(
                            "tool_failed",
                            {**audit, "status": "error", "error": result["error"]},
                        )
                    else:
                        signature = _tool_signature(name, args)
                        audit = _tool_audit(
                            round_number=round_index + 1,
                            name=name,
                            args=args,
                            signature=signature,
                        )
                        audit["raw_args"] = raw_args
                        yield OpenClawStreamEvent("tool_started", {**audit, "status": "started"})
                        if total_tool_calls > max_rounds * 4:
                            result = {"status": "ERROR", "error": "工具调用总数达到安全上限"}
                            tool_events.append({**audit, "status": "error", "summary": result["error"]})
                            yield OpenClawStreamEvent(
                                "tool_failed",
                                {**audit, "status": "error", "error": result["error"]},
                            )
                        elif signature in seen_call_signatures:
                            result = {"status": "ERROR", "error": "检测到重复工具调用，已阻止重复执行"}
                            audit["duplicate_blocked"] = True
                            tool_events.append({**audit, "status": "error", "summary": result["error"]})
                            yield OpenClawStreamEvent(
                                "tool_failed",
                                {**audit, "status": "error", "error": result["error"]},
                            )
                        elif name not in self.specs:
                            result = {"status": "ERROR", "error": f"工具未被允许：{name}"}
                            tool_events.append({**audit, "status": "error", "summary": result["error"]})
                            yield OpenClawStreamEvent(
                                "tool_failed",
                                {**audit, "status": "error", "error": result["error"]},
                            )
                        else:
                            seen_call_signatures.add(signature)
                            try:
                                result = self.specs[name].handler(args)
                                summary = _tool_summary(name, result)
                                tool_events.append({**audit, "status": "done", "summary": summary})
                                yield OpenClawStreamEvent(
                                    "tool_completed",
                                    {**audit, "status": "done", "summary": summary},
                                )
                            except Exception as exc:  # tool errors must return to the model
                                result = {"status": "ERROR", "error": f"工具执行失败：{exc}"}
                                tool_events.append({**audit, "status": "error", "summary": result["error"]})
                                yield OpenClawStreamEvent(
                                    "tool_failed",
                                    {**audit, "status": "error", "error": result["error"]},
                                )

                    request_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": _openclaw_tool_payload(name, result),
                        }
                    )

        fallback = (
            "工具分析已达到安全轮次上限，未取得最终模型结论；"
            "系统未将工具轮中的草稿作为结论。请查看工具审计并补充缺失条件后重试。"
        )
        if visible_content.strip():
            fallback = visible_content
        else:
            # No delta was sent in any round, so the terminal fallback needs
            # one visible chunk.  If content was already streamed, the final
            # event carries it as metadata without replaying it as a delta.
            yield OpenClawStreamEvent("answer_delta", {"text": fallback})
        yield OpenClawStreamEvent(
            "answer_completed",
            {
                "status": "FINAL",
                "narrative": fallback,
                "tool_calls": tool_events,
                "usage": usage,
                "rounds": max_rounds,
            },
        )


def _tool_summary(name: str, result: Any) -> str:
    if not isinstance(result, dict):
        return f"{name} 已返回结果"
    if result.get("status") in {"ERROR", "NOT_FOUND"}:
        return str(result.get("error") or result.get("status"))
    if name in {"calculate_cbu_tax", "calculate_ckd_tax"}:
        return "税负计算结果已返回"
    if name == "search_policy_rules":
        return f"已找到 {result.get('total', 0)} 条政策规则"
    if name == "get_policy_evidence":
        return "政策原文证据已返回"
    if name == "inspect_data_coverage":
        return f"数据覆盖状态：{result.get('coverage_status', '未知')}"
    if name == "gais_web_search":
        return f"已返回 {len(result.get('results', []))} 条网络搜索结果"
    return "工具结果已返回"


def _web_search(settings: Settings, args: dict[str, Any]) -> dict[str, Any]:
    """Call a configured public search provider without exposing its key.

    The adapter intentionally returns a structured NOT_CONFIGURED response
    when no key/provider is present.  The model can then state the limitation
    instead of hallucinating a search result.
    """

    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "ERROR", "error": "query 不能为空", "results": []}
    try:
        count = max(1, min(int(args.get("count") or settings.web_search_max_results), 10))
    except (TypeError, ValueError):
        count = max(1, min(settings.web_search_max_results, 10))
    provider = (settings.web_search_provider or "brave").strip().lower()
    country_context = str(args.get("country") or "").strip()
    # Tavily has no country parameter equivalent to Brave's country filter.
    # Prefixing the requested country keeps Vietnam/Malaysia policy searches
    # scoped without changing the caller-visible audit query.  Do not alter
    # Brave's existing request shape: it already receives ``country`` as a
    # provider parameter.
    provider_query = query
    if provider == "tavily" and country_context and country_context.casefold() not in query.casefold():
        provider_query = f"{country_context} {query}".strip()

    if provider == "tavily":
        api_key = settings.tavily_api_key.strip()
        if not api_key:
            return {
                "status": "NOT_CONFIGURED",
                "provider": "tavily",
                "required": "GAIS_TAVILY_API_KEY",
                "query": query,
                "search_query": provider_query,
                "country": country_context or None,
                "results": [],
            }
        payload: dict[str, Any] = {
            "query": provider_query,
            "max_results": count,
            "search_depth": str(args.get("search_depth") or "advanced"),
            "topic": str(args.get("topic") or "general"),
            "include_answer": False,
            "include_raw_content": "markdown",
        }
        if args.get("time_range"):
            payload["time_range"] = str(args["time_range"])
        domains = args.get("include_domains")
        if isinstance(domains, list):
            payload["include_domains"] = [str(domain) for domain in domains[:20] if str(domain).strip()]
        try:
            with httpx.Client(timeout=25.0) as client:
                response = client.post(
                    "https://api.tavily.com/search",
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
            results = [
                {
                    "title": str(item.get("title") or "")[:300],
                    "url": str(item.get("url") or ""),
                    "snippet": str(item.get("content") or "")[:800],
                    "raw_content": str(item.get("raw_content") or "")[:6000],
                    "score": item.get("score"),
                }
                for item in (data.get("results") or [])[:count]
                if item.get("url")
            ]
            return {
                "status": "OK",
                "provider": "tavily",
                "query": query,
                "search_query": provider_query,
                "country": country_context or None,
                "results": results,
            }
        except (httpx.HTTPError, ValueError) as exc:
            return {
                "status": "ERROR",
                "provider": "tavily",
                "query": query,
                "search_query": provider_query,
                "country": country_context or None,
                "error": str(exc),
                "results": [],
            }

    if provider == "searxng":
        base_url = settings.searxng_base_url.strip().rstrip("/")
        if not base_url:
            return {
                "status": "NOT_CONFIGURED",
                "provider": "searxng",
                "required": "GAIS_SEARXNG_BASE_URL",
                "query": query,
                "country": country_context or None,
                "results": [],
            }
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(
                    urljoin(base_url + "/", "search"),
                    params={"q": query, "format": "json", "language": "auto"},
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
            results = [
                {
                    "title": str(item.get("title") or "")[:300],
                    "url": str(item.get("url") or ""),
                    "snippet": str(item.get("content") or "")[:800],
                }
                for item in (data.get("results") or [])[:count]
                if item.get("url")
            ]
            return {
                "status": "OK",
                "provider": "searxng",
                "query": query,
                "country": country_context or None,
                "results": results,
            }
        except (httpx.HTTPError, ValueError) as exc:
            return {
                "status": "ERROR",
                "provider": "searxng",
                "query": query,
                "country": country_context or None,
                "error": str(exc),
                "results": [],
            }

    api_key = settings.brave_api_key.strip()
    if not api_key:
        return {
            "status": "NOT_CONFIGURED",
            "provider": "brave",
            "required": "GAIS_BRAVE_API_KEY",
            "query": query,
            "country": country_context or None,
            "results": [],
        }
    params: dict[str, Any] = {"q": query, "count": count}
    for key in ("country", "freshness"):
        if args.get(key):
            params[key] = str(args[key])
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params=params,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
        results = [
            {
                "title": str(item.get("title") or "")[:300],
                "url": str(item.get("url") or ""),
                "snippet": str(item.get("description") or "")[:800],
            }
            for item in (data.get("web", {}).get("results") or [])[:count]
            if item.get("url")
        ]
        return {
            "status": "OK",
            "provider": "brave",
            "query": query,
            "country": country_context or None,
            "results": results,
        }
    except (httpx.HTTPError, ValueError) as exc:
        return {
            "status": "ERROR",
            "provider": "brave",
            "query": query,
            "country": country_context or None,
            "error": str(exc),
            "results": [],
        }
