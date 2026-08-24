"""Pure unit tests for OpenClaw streaming event assembly.

These tests replace the HTTP client with an in-memory async stream.  They do
not require a running Gateway, a model credential, or a database.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.core.config import Settings
from app.services import openclaw_client as module
from app.services.openclaw_client import OpenClawClient


def _line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}"


class _FakeResponse:
    status_code = 200

    def __init__(self, lines: list[str]):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def aread(self) -> bytes:
        return b""

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeClient:
    def __init__(self, responses: list[list[str]], **_kwargs):
        self.responses = responses
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def stream(self, *_args, **_kwargs):
        response = _FakeResponse(self.responses[min(self.calls, len(self.responses) - 1)])
        self.calls += 1
        return response


def _collect(client: OpenClawClient):
    async def run():
        return [event async for event in client.chat_stream(conversation_id="test", messages=[])]

    return asyncio.run(run())


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "openclaw_enabled": True,
        "openclaw_base_url": "http://gateway.invalid",
        "openclaw_gateway_token": "unit-test-token",
    }
    values.update(overrides)
    return Settings(**values)


def test_streaming_delta_preserves_repeated_tokens(monkeypatch):
    response = [
        _line({"choices": [{"delta": {"content": "A"}}]}),
        _line({"choices": [{"delta": {"content": "A"}}]}),
        _line({"choices": [{"delta": {"content": "B"}}]}),
        _line({"choices": [{"delta": {}}]}),
        "data: [DONE]",
    ]
    fake = _FakeClient([response])
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **_kwargs: fake)

    events = _collect(OpenClawClient(_settings()))
    deltas = [event.data["text"] for event in events if event.event == "answer_delta"]
    completed = [event for event in events if event.event == "answer_completed"]

    assert deltas == ["A", "A", "B"]
    assert completed[-1].data["narrative"] == "AAB"


def test_round_limit_does_not_expose_tool_round_draft(monkeypatch):
    response = [
        _line(
            {
                "choices": [
                    {
                        "delta": {
                            "content": "already",
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call-1",
                                    "function": {"name": "blocked_tool", "arguments": "{}"},
                                }
                            ],
                        }
                    }
                ]
            }
        ),
        "data: [DONE]",
    ]
    fake = _FakeClient([response])
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **_kwargs: fake)

    events = _collect(OpenClawClient(_settings(openclaw_max_tool_rounds=1)))
    deltas = [event.data["text"] for event in events if event.event == "answer_delta"]
    completed = [event for event in events if event.event == "answer_completed"]

    # Text generated in a round that also requests a tool is only a draft. It
    # must not be shown as a grounded answer, even when the tool loop reaches
    # its safety limit before a final synthesis round.
    assert "already" not in "".join(deltas)
    assert "already" not in completed[-1].data["narrative"]
    assert "安全轮次上限" in completed[-1].data["narrative"]
