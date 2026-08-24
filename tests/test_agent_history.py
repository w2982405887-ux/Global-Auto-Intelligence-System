"""Account ownership and PostgreSQL persistence tests for assistant history."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import select

from app.agent import router as agent_router
from app.auth.models import Organization, UserAccount
from app.auth.security import utcnow
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app


@contextmanager
def _db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(get_settings().auth_csrf_cookie_name)
    assert token
    return {get_settings().auth_csrf_header_name: token}


def _login(client: TestClient, email: str, organization_key: str) -> None:
    response = client.post(
        "/api/v1/auth/dev/login",
        json={"email": email, "organization_code": organization_key},
    )
    assert response.status_code == 200, response.text


def _cleanup(email: str, organization_key: str) -> None:
    with _db() as db:
        user = db.scalar(select(UserAccount).where(UserAccount.email == email))
        organization = db.scalar(
            select(Organization).where(Organization.organization_key == organization_key)
        )
        if user is not None:
            db.delete(user)
        if organization is not None:
            db.delete(organization)
        db.commit()


class _FakeSnapshot:
    def __init__(self, values: dict):
        self.values = values


class _FakeAgent:
    """Small deterministic graph double; no model/network call is made."""

    def __init__(self):
        self._states: dict[str, dict] = {}
        self.last_initial_state: dict | None = None

    def get_state(self, config):
        return _FakeSnapshot(self._states[config["configurable"]["thread_id"]]) if config["configurable"]["thread_id"] in self._states else None

    async def astream(self, initial_state, config):
        self.last_initial_state = initial_state
        conversation_id = config["configurable"]["thread_id"]
        answer = AIMessage(content="这是一个用于验证数据库持久化和账号隔离的测试回答。")
        self._states[conversation_id] = {
            **initial_state,
            "messages": list(initial_state["messages"]) + [answer],
            "status": "done",
        }
        yield {"agent_node": {"status": "done", "messages": [answer]}}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GAIS_AUTH_LOCAL_DEV_ENABLED", "true")
    monkeypatch.setenv("GAIS_AUTH_SECRET_KEY", "iam-history-test-secret")
    monkeypatch.setenv("GAIS_OPENCLAW_ENABLED", "false")
    get_settings.cache_clear()
    if not get_settings().auth_local_dev_enabled:
        pytest.skip("local login is disabled")
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_chat_history_is_persisted_and_isolated_by_account(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = _FakeAgent()
    monkeypatch.setattr(agent_router, "get_agent", lambda: agent)
    email_a = f"history-a-{uuid4().hex}@example.local"
    email_b = f"history-b-{uuid4().hex}@example.local"
    org_a = f"HISTORY-{uuid4().hex[:12]}"
    org_b = f"HISTORY-{uuid4().hex[:12]}"
    conversation_id = "history-" + uuid4().hex

    try:
        _login(client, email_a, org_a)
        created = client.post(
            "/api/v1/assistant/chat",
            headers=_csrf_headers(client),
            json={
                "conversation_id": conversation_id,
                "message": "请保存这条消息",
                "stream": False,
            },
        )
        assert created.status_code == 200, created.text
        assert created.json()["conversation_id"] == conversation_id

        # Both the router cache and graph object are replaced to emulate a
        # backend restart.  Reads and the next model context must come from
        # PostgreSQL rather than process memory.
        agent_router._conversations.clear()
        restarted_agent = _FakeAgent()
        monkeypatch.setattr(agent_router, "get_agent", lambda: restarted_agent)
        messages = client.get(
            f"/api/v1/assistant/conversations/{conversation_id}/messages"
        )
        assert messages.status_code == 200, messages.text
        assert [item["role"] for item in messages.json()["messages"]] == [
            "user",
            "assistant",
        ]
        assert messages.json()["messages"][0]["content"] == "请保存这条消息"

        continued = client.post(
            "/api/v1/assistant/chat",
            headers=_csrf_headers(client),
            json={
                "conversation_id": conversation_id,
                "message": "后端重启后继续对话",
                "stream": True,
            },
        )
        assert continued.status_code == 200, continued.text
        assert restarted_agent.last_initial_state is not None
        hydrated = restarted_agent.last_initial_state["messages"]
        assert [item.type for item in hydrated] == ["human", "ai", "human"]
        assert [item.content for item in hydrated] == [
            "请保存这条消息",
            "这是一个用于验证数据库持久化和账号隔离的测试回答。",
            "后端重启后继续对话",
        ]

        messages = client.get(
            f"/api/v1/assistant/conversations/{conversation_id}/messages"
        )
        assert [item["role"] for item in messages.json()["messages"]] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]

        listed = client.get("/api/v1/assistant/conversations")
        assert listed.status_code == 200, listed.text
        assert [item["conversation_id"] for item in listed.json()] == [conversation_id]

        with TestClient(app) as client_b:
            _login(client_b, email_b, org_b)
            assert client_b.get("/api/v1/assistant/conversations").json() == []
            for path in (
                f"/api/v1/assistant/conversations/{conversation_id}/messages",
                f"/api/v1/assistant/{conversation_id}/state",
            ):
                assert client_b.get(path).status_code == 404
            assert client_b.patch(
                f"/api/v1/assistant/conversations/{conversation_id}",
                headers=_csrf_headers(client_b),
                json={"title": "越权修改"},
            ).status_code == 404
            assert client_b.delete(
                f"/api/v1/assistant/conversations/{conversation_id}",
                headers=_csrf_headers(client_b),
            ).status_code == 404
    finally:
        _cleanup(email_a, org_a)
        _cleanup(email_b, org_b)
