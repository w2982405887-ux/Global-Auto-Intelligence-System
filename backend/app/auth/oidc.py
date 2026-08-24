"""OpenID Connect discovery, authorization-code exchange and ID-token checks."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings

try:  # PyJWT[crypto] is an application dependency; keep imports optional for offline tests.
    import jwt
except ImportError:  # pragma: no cover - exercised only in minimal installations
    jwt = None  # type: ignore[assignment]


class OIDCError(RuntimeError):
    """A safe-to-expose OIDC configuration/provider failure."""


@dataclass(frozen=True)
class OIDCConfiguration:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str | None


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def create_pkce_verifier() -> str:
    # RFC 7636 permits 43-128 chars. token_urlsafe(48) yields 64 chars.
    import secrets

    return secrets.token_urlsafe(48)


def pkce_challenge(verifier: str) -> str:
    return _b64(hashlib.sha256(verifier.encode("ascii")).digest())


async def discover(settings: Settings) -> OIDCConfiguration:
    issuer = settings.auth_oidc_issuer_url.rstrip("/")
    if not issuer:
        raise OIDCError("OIDC issuer is not configured")
    url = f"{issuer}/.well-known/openid-configuration"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OIDCError("OIDC discovery failed") from exc
    if data.get("issuer", issuer).rstrip("/") != issuer:
        raise OIDCError("OIDC discovery issuer mismatch")
    required = ("authorization_endpoint", "token_endpoint", "jwks_uri")
    if any(not isinstance(data.get(key), str) or not data[key] for key in required):
        raise OIDCError("OIDC discovery is missing required endpoints")
    return OIDCConfiguration(
        issuer=issuer,
        authorization_endpoint=data["authorization_endpoint"],
        token_endpoint=data["token_endpoint"],
        jwks_uri=data["jwks_uri"],
        userinfo_endpoint=data.get("userinfo_endpoint"),
    )


def authorization_url(
    configuration: OIDCConfiguration,
    settings: Settings,
    *,
    state: str,
    nonce: str,
    verifier: str,
) -> str:
    from urllib.parse import urlencode

    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.auth_oidc_client_id,
            "redirect_uri": settings.auth_oidc_redirect_uri,
            "scope": settings.auth_oidc_scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
    )
    return f"{configuration.authorization_endpoint}?{query}"


async def exchange_code(
    configuration: OIDCConfiguration,
    settings: Settings,
    *,
    code: str,
    verifier: str,
) -> dict[str, Any]:
    if not settings.auth_oidc_client_id or not settings.auth_oidc_client_secret:
        raise OIDCError("OIDC client credentials are not configured")
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.auth_oidc_redirect_uri,
        "client_id": settings.auth_oidc_client_id,
        "client_secret": settings.auth_oidc_client_secret,
        "code_verifier": verifier,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.post(configuration.token_endpoint, data=payload)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OIDCError("OIDC token exchange failed") from exc
    if not isinstance(data, dict) or not data.get("id_token"):
        raise OIDCError("OIDC provider did not return an ID token")
    return data


async def validate_id_token(
    configuration: OIDCConfiguration,
    settings: Settings,
    id_token: str,
    *,
    expected_nonce: str,
) -> dict[str, Any]:
    if jwt is None:
        raise OIDCError("PyJWT[crypto] is required for OIDC ID-token validation")
    try:
        header = jwt.get_unverified_header(id_token)
        unverified_claims = jwt.decode(id_token, options={"verify_signature": False})
    except Exception as exc:
        raise OIDCError("OIDC ID token is malformed") from exc
    kid = header.get("kid")
    algorithm = header.get("alg")
    if not kid or algorithm not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}:
        raise OIDCError("OIDC ID token uses an unsupported signing key")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(configuration.jwks_uri)
            response.raise_for_status()
            jwks = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OIDCError("OIDC JWKS retrieval failed") from exc
    keys = jwks.get("keys", []) if isinstance(jwks, dict) else []
    key_data = next((key for key in keys if key.get("kid") == kid), None)
    if key_data is None:
        raise OIDCError("OIDC signing key was not found")
    try:
        signing_key = jwt.PyJWK.from_dict(key_data).key
        claims = jwt.decode(
            id_token,
            key=signing_key,
            algorithms=[algorithm],
            audience=settings.auth_oidc_client_id,
            issuer=configuration.issuer,
            options={"require": ["exp", "iat", "iss", "sub", "aud", "nonce"]},
        )
    except Exception as exc:
        raise OIDCError("OIDC ID token validation failed") from exc
    if claims.get("nonce") != expected_nonce or claims.get("sub") != unverified_claims.get("sub"):
        raise OIDCError("OIDC nonce validation failed")
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise OIDCError("OIDC subject is missing")
    return dict(claims)


async def userinfo(
    configuration: OIDCConfiguration,
    access_token: str,
) -> dict[str, Any]:
    if not configuration.userinfo_endpoint:
        return {}
    if not access_token:
        return {}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(
                configuration.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OIDCError("OIDC userinfo retrieval failed") from exc
    return data if isinstance(data, dict) else {}
