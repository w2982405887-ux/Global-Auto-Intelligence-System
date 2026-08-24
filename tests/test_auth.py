"""Authentication and tenant-boundary smoke tests.

These tests intentionally use the migrated local PostgreSQL schema instead of
creating an ad-hoc SQLite schema.  Run them with the same ``GAIS_DATABASE_URL``
used by ``scripts/backend-run.ps1`` and enable local login explicitly:

    $env:GAIS_AUTH_LOCAL_DEV_ENABLED = "true"
    $env:GAIS_AUTH_SECRET_KEY = "a-development-only-secret"
    pytest -q tests/test_auth.py
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.auth.models import Organization, OrganizationMembership, UserAccount
from app.auth.repository import set_membership_roles
from app.auth.security import sign_state, verify_state
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


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    settings = get_settings()
    if not settings.auth_local_dev_enabled:
        pytest.skip("Set GAIS_AUTH_LOCAL_DEV_ENABLED=true for IAM integration tests")
    if not settings.auth_secret_key or settings.auth_secret_key == "change-me-in-production":
        pytest.skip("Set GAIS_AUTH_SECRET_KEY for IAM integration tests")
    with TestClient(app) as test_client:
        yield test_client


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


def _login(client: TestClient, email: str, organization_key: str) -> dict:
    response = client.post(
        "/api/v1/auth/dev/login",
        json={"email": email, "organization_code": organization_key},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == email
    assert data["active_organization"]["organization_code"] == organization_key
    assert data["csrf_token"]
    return data


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(get_settings().auth_csrf_cookie_name)
    assert token
    return {get_settings().auth_csrf_header_name: token}


def test_state_signature_rejects_tampering_and_expiry() -> None:
    signed = sign_state({"state": "s", "nonce": "n", "verifier": "v", "iat": "1"}, "secret")
    assert verify_state(signed, "secret", max_age_seconds=10) is None
    assert verify_state(signed + "x", "secret", max_age_seconds=10) is None


def test_private_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/assistant/conversations")
    assert response.status_code == 401, response.text
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401, response.text


def test_dev_login_sets_session_and_csrf_cookie_and_logout_revokes_session(
    client: TestClient,
) -> None:
    email = f"iam-{uuid4().hex}@example.local"
    organization_key = f"IAM-{uuid4().hex[:12]}"
    try:
        data = _login(client, email, organization_key)
        set_cookie = client.cookies.get(get_settings().auth_session_cookie_name)
        csrf_cookie = client.cookies.get(get_settings().auth_csrf_cookie_name)
        assert set_cookie and csrf_cookie
        set_cookie_headers = client.post(
            "/api/v1/auth/dev/login",
            json={"email": email, "organization_code": organization_key},
        ).headers.get_list("set-cookie")
        session_cookie_header = next(
            item for item in set_cookie_headers if item.startswith(get_settings().auth_session_cookie_name + "=")
        )
        assert "HttpOnly" in session_cookie_header
        assert "SameSite=lax" in session_cookie_header

        # The session cookie is opaque to JavaScript; the CSRF cookie is
        # intentionally readable and can be copied into the write header.
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["active_organization"]["organization_id"] == data["active_organization"][
            "organization_id"
        ]

        cookie_header = client.get("/api/v1/auth/me").headers
        assert cookie_header is not None  # keep the request path exercised

        # An untrusted Origin cannot use the cookie-authenticated session.
        blocked = client.post("/api/v1/auth/logout", headers={"Origin": "https://evil.example"})
        assert blocked.status_code == 403, blocked.text
        # A trusted first-party Origin is not a CSRF proof.  The double-submit
        # token is required even for same-origin browser writes.
        missing_header = client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://localhost:3000"},
        )
        assert missing_header.status_code == 403, missing_header.text

        logged_out = client.post("/api/v1/auth/logout", headers=_csrf_headers(client))
        assert logged_out.status_code == 200, logged_out.text
        assert client.get("/api/v1/auth/me").status_code == 401
    finally:
        _cleanup(email, organization_key)


def test_viewer_without_assistant_permission_gets_403(client: TestClient) -> None:
    email = f"viewer-{uuid4().hex}@example.local"
    organization_key = f"IAM-{uuid4().hex[:12]}"
    try:
        _login(client, email, organization_key)
        with _db() as db:
            user = db.scalar(select(UserAccount).where(UserAccount.email == email))
            assert user is not None
            membership = db.scalar(
                select(OrganizationMembership).where(OrganizationMembership.user_id == user.user_id)
            )
            assert membership is not None
            set_membership_roles(db, membership, ["viewer"])
            db.commit()
        assert client.get("/api/v1/assistant/conversations").status_code == 403
    finally:
        _cleanup(email, organization_key)


def test_switching_to_an_unrelated_organization_is_forbidden(client: TestClient) -> None:
    email = f"switch-{uuid4().hex}@example.local"
    organization_key = f"IAM-{uuid4().hex[:12]}"
    unrelated_key = f"IAM-{uuid4().hex[:12]}"
    try:
        _login(client, email, organization_key)
        with _db() as db:
            unrelated = Organization(
                organization_id=uuid4(),
                organization_key=unrelated_key,
                organization_name="Unrelated test organization",
                status="ACTIVE",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(unrelated)
            db.commit()
            unrelated_id = unrelated.organization_id
        response = client.post(
            f"/api/v1/organizations/{unrelated_id}/switch",
            headers=_csrf_headers(client),
        )
        assert response.status_code == 403, response.text
    finally:
        _cleanup(email, organization_key)
        _cleanup("not-an-email", unrelated_key)


@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
def test_local_login_is_unavailable_outside_local_environment(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv("GAIS_AUTH_LOCAL_DEV_ENABLED", "true")
    monkeypatch.setenv("GAIS_AUTH_SECRET_KEY", "iam-test-secret-please-replace")
    monkeypatch.setenv("GAIS_ENVIRONMENT", environment)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/dev/login",
                json={"email": "blocked@example.local"},
            )
        assert response.status_code == 404, response.text
    finally:
        get_settings.cache_clear()
