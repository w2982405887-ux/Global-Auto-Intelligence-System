"""Pure tests for the public OpenClaw-to-SSE heartbeat bridge."""

from __future__ import annotations

import asyncio

from app.agent.router import _openclaw_events_with_heartbeats
from app.services.openclaw_client import OpenClawStreamEvent


def _run(coro):
    return asyncio.run(coro)


def test_bridge_emits_heartbeat_while_gateway_is_idle() -> None:
    async def gateway_events():
        await asyncio.sleep(0.035)
        yield OpenClawStreamEvent("answer_completed", {"narrative": "done"})

    async def collect():
        return [
            event
            async for event in _openclaw_events_with_heartbeats(
                gateway_events(), heartbeat_interval=0.01
            )
        ]

    events = _run(collect())
    assert any(
        event.event == "status" and event.data.get("heartbeat") is True
        for event in events
    )
    assert events[-1].event == "answer_completed"


def test_bridge_preserves_normal_completion_without_extra_terminal_event() -> None:
    async def gateway_events():
        yield OpenClawStreamEvent("answer_delta", {"text": "ok"})
        yield OpenClawStreamEvent("answer_completed", {"narrative": "ok"})

    async def collect():
        return [event async for event in _openclaw_events_with_heartbeats(gateway_events())]

    events = _run(collect())
    assert [event.event for event in events] == ["answer_delta", "answer_completed"]


def test_bridge_cancels_pending_gateway_read_and_closes_generator() -> None:
    closed = False

    async def gateway_events():
        nonlocal closed
        try:
            await asyncio.Event().wait()
            yield OpenClawStreamEvent("answer_completed", {"narrative": "never"})
        finally:
            closed = True

    async def cancel_consumer():
        stream = _openclaw_events_with_heartbeats(gateway_events(), heartbeat_interval=0.01)
        task = asyncio.create_task(stream.__anext__())
        await asyncio.sleep(0.025)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await stream.aclose()

    _run(cancel_consumer())
    assert closed is True

