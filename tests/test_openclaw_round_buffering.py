"""Regression tests for OpenClaw multi-round visibility and tool auditing."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.core.config import Settings
from app.services import openclaw_client as module
from app.services.openclaw_client import OpenClawClient, ToolSpec


def _line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}"


class _Response:
    status_code = 200

    def __init__(self, lines: list[str]):
        self.lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def aread(self) -> bytes:
        return b""

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class _Client:
    def __init__(self, responses: list[list[str]], **_kwargs):
        self.responses = responses
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def stream(self, *_args, **_kwargs):
        response = _Response(self.responses[min(self.calls, len(self.responses) - 1)])
        self.calls += 1
        return response


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "openclaw_enabled": True,
        "openclaw_base_url": "http://gateway.invalid",
        "openclaw_gateway_token": "unit-test-token",
        "openclaw_max_tool_rounds": 4,
    }
    values.update(overrides)
    return Settings(**values)


def _tool_round(call_id: str, args: dict[str, Any], draft: str = "模型草稿") -> list[str]:
    return [
        _line(
            {
                "choices": [
                    {
                        "delta": {
                            "content": draft,
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": call_id,
                                    "function": {
                                        "name": "test_tool",
                                        "arguments": json.dumps(args, ensure_ascii=False),
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        ),
        "data: [DONE]",
    ]


def _final_round(text: str) -> list[str]:
    return [
        _line({"choices": [{"delta": {"content": text}}]}),
        "data: [DONE]",
    ]


def _collect(client: OpenClawClient):
    async def run():
        return [event async for event in client.chat_stream(conversation_id="test", messages=[])]

    return asyncio.run(run())


def _client(monkeypatch, responses: list[list[str]]) -> OpenClawClient:
    fake = _Client(responses)
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **_kwargs: fake)
    client = OpenClawClient(_settings())
    client.specs = {
        "test_tool": ToolSpec(
            name="test_tool",
            description="unit test tool",
            handler=lambda args: {"status": "OK", "echo": args},
            parameters={"type": "object", "additionalProperties": True},
        )
    }
    return client


def test_tool_round_draft_is_not_exposed_and_final_round_is_visible(monkeypatch):
    client = _client(
        monkeypatch,
        [_tool_round("call-1", {"country": "VN"}, draft="未经取证的草稿"), _final_round("已核验的最终结论")],
    )

    events = _collect(client)
    deltas = [event.data["text"] for event in events if event.event == "answer_delta"]
    completed = next(event for event in events if event.event == "answer_completed")
    tools = completed.data["tool_calls"]

    assert deltas == ["已核验的最终结论"]
    assert "未经取证的草稿" not in "".join(deltas)
    assert completed.data["narrative"] == "已核验的最终结论"
    assert tools[0]["round"] == 1
    assert tools[0]["args"] == {"country": "VN"}
    assert tools[0]["signature"].startswith("test_tool:")
    assert tools[0]["duplicate_blocked"] is False


def test_exact_duplicate_is_blocked_but_a_different_refinement_is_allowed(monkeypatch):
    client = _client(
        monkeypatch,
        [
            _tool_round("call-1", {"value": 1}, draft="第一轮草稿"),
            _tool_round("call-2", {"value": 1}, draft="重复调用草稿"),
            _final_round("最终回答"),
        ],
    )

    events = _collect(client)
    completed = next(event for event in events if event.event == "answer_completed")
    tools = completed.data["tool_calls"]
    failed = [event for event in events if event.event == "tool_failed"]

    assert completed.data["narrative"] == "最终回答"
    assert len(tools) == 2
    assert tools[0]["duplicate_blocked"] is False
    assert tools[1]["duplicate_blocked"] is True
    assert tools[0]["signature"] == tools[1]["signature"]
    assert failed[-1].data["duplicate_blocked"] is True
    assert all("草稿" not in event.data.get("text", "") for event in events if event.event == "answer_delta")
