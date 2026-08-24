"""Personal-account and assistant-history isolation integration tests.

These tests intentionally use the migrated PostgreSQL schema.  They do not
create an ad-hoc SQLite database or organization records: a personal account
must be usable without an organization, and assistant conversations must be
owned by exactly one account.

Run from the project root with the backend on ``PYTHONPATH``::

    $env:PYTHONPATH = "backend"
    pytest -q tests/test_personal_auth.py

The database must have the IAM and assistant-history migrations applied.  The
test fixture disables OpenClaw and replaces the legacy agent with a deterministic
double, so no model or network credential is needed.
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import select

from app.agent import router as agent_router
from app.auth.models import UserAccount
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
    settings = get_settings()
    token = client.cookies.get(settings.auth_csrf_cookie_name)
    assert token, "personal login must issue a readable CSRF cookie"
    return {settings.auth_csrf_header_name: token}


def _register(client: TestClient, email: str, password: str = "Test-pass-123") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Personal tester"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _cleanup(email: str) -> None:
    # assistant.conversation and iam.session reference the account with
    # database-level cascade rules; deleting the account removes only this
    # test user's data and never touches another account or organization.
    with _db() as db:
        user = db.scalar(select(UserAccount).where(UserAccount.email == email.lower()))
        if user is not None:
            db.delete(user)
            db.commit()


@pytest.fixture
def personal_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GAIS_AUTH_PERSONAL_ENABLED", "true")
    monkeypatch.setenv("GAIS_AUTH_SECRET_KEY", "personal-auth-test-secret")
    monkeypatch.setenv("GAIS_OPENCLAW_ENABLED", "false")
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


def test_personal_registration_login_and_logout_require_no_organization(
    personal_client: TestClient,
) -> None:
    email = f"personal-{uuid4().hex}@example.local"
    password = "Test-pass-123"
    try:
        # Registration normalizes the stable account identifier and logs the
        # user in immediately, without creating/selecting an organization.
        registered = _register(personal_client, f"  {email.upper()}  ", password)
        assert registered["authenticated"] is True
        assert registered["user"]["email"] == email
        assert registered["organizations"] == []
        assert registered["active_organization"] is None
        assert registered["current_organization"] is None
        assert "assistant.chat" in registered["permissions"]
        assert personal_client.cookies.get(get_settings().auth_session_cookie_name)
        assert personal_client.cookies.get(get_settings().auth_csrf_cookie_name)

        with _db() as db:
            user = db.scalar(select(UserAccount).where(UserAccount.email == email))
            assert user is not None
            assert user.identity_provider == "personal"
            assert user.password_hash
            assert password not in user.password_hash

        # The unique-email contract is case-insensitive and must not create a
        # second account when the casing differs.
        duplicate = personal_client.post(
            "/api/v1/auth/register",
            json={"email": email.upper(), "password": password},
        )
        assert duplicate.status_code == 409, duplicate.text

        # Login accepts the normalized identifier but rejects invalid
        # credentials with the same generic response.
        assert personal_client.post(
            "/api/v1/auth/logout"
        ).status_code == 403  # double-submit CSRF is required
        wrong = personal_client.post(
            "/api/v1/auth/login",
            json={"email": email.upper(), "password": "wrong-password"},
        )
        assert wrong.status_code == 401, wrong.text
        logged_in = personal_client.post(
            "/api/v1/auth/login",
            json={"email": email.upper(), "password": password},
        )
        assert logged_in.status_code == 200, logged_in.text
        assert logged_in.json()["active_organization"] is None
        assert personal_client.get("/api/v1/auth/me").status_code == 200

        logged_out = personal_client.post(
            "/api/v1/auth/logout", headers=_csrf_headers(personal_client)
        )
        assert logged_out.status_code == 200, logged_out.text
        assert personal_client.get("/api/v1/auth/me").status_code == 401
    finally:
        _cleanup(email)


class _FakeSnapshot:
    def __init__(self, values: dict):
        self.values = values


class _FakeAgent:
    """Deterministic graph double; the test never calls an LLM or network."""

    def __init__(self):
        self._states: dict[str, dict] = {}

    def get_state(self, config):
        conversation_id = config["configurable"]["thread_id"]
        values = self._states.get(conversation_id)
        return _FakeSnapshot(values) if values is not None else None

    async def astream(self, initial_state, config):
        conversation_id = config["configurable"]["thread_id"]
        answer = AIMessage(content="这是个人账号隔离测试的确定性回答。")
        self._states[conversation_id] = {
            **initial_state,
            "messages": list(initial_state["messages"]) + [answer],
            "status": "done",
        }
        yield {"agent_node": {"status": "done", "messages": [answer]}}


def test_assistant_history_isolated_between_personal_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GAIS_AUTH_PERSONAL_ENABLED", "true")
    monkeypatch.setenv("GAIS_AUTH_SECRET_KEY", "personal-history-test-secret")
    monkeypatch.setenv("GAIS_OPENCLAW_ENABLED", "false")
    get_settings.cache_clear()
    fake_agent = _FakeAgent()
    monkeypatch.setattr(agent_router, "get_agent", lambda: fake_agent)

    email_a = f"history-a-{uuid4().hex}@example.local"
    email_b = f"history-b-{uuid4().hex}@example.local"
    conversation_id = "personal-history-" + uuid4().hex
    try:
        with TestClient(app) as client_a:
            _register(client_a, email_a)
            created = client_a.post(
                "/api/v1/assistant/chat",
                headers=_csrf_headers(client_a),
                json={
                    "conversation_id": conversation_id,
                    "message": "只属于账号 A 的消息",
                    "stream": False,
                },
            )
            assert created.status_code == 200, created.text
            assert created.json()["conversation_id"] == conversation_id

            listed_a = client_a.get("/api/v1/assistant/conversations")
            assert listed_a.status_code == 200, listed_a.text
            assert [item["conversation_id"] for item in listed_a.json()] == [conversation_id]
            messages_a = client_a.get(
                f"/api/v1/assistant/conversations/{conversation_id}/messages"
            )
            assert messages_a.status_code == 200, messages_a.text
            assert [item["role"] for item in messages_a.json()["messages"]] == [
                "user",
                "assistant",
            ]

        with TestClient(app) as client_b:
            _register(client_b, email_b)
            assert client_b.get("/api/v1/assistant/conversations").json() == []

            # Every read and write path must enforce ownership, not merely
            # rely on an opaque conversation id being hard to guess.
            assert client_b.get(
                f"/api/v1/assistant/conversations/{conversation_id}/messages"
            ).status_code == 404
            assert client_b.get(
                f"/api/v1/assistant/{conversation_id}/state"
            ).status_code == 404
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
        _cleanup(email_a)
        _cleanup(email_b)
        get_settings.cache_clear()
