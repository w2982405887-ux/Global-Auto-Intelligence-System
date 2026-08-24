"""Small, dependency-light primitives used by the authentication layer."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 16


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_token(byte_length: int = 32) -> str:
    return secrets.token_urlsafe(byte_length)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str, *, iterations: int = PASSWORD_ITERATIONS) -> str:
    """Return a self-describing PBKDF2-SHA256 password hash.

    Passwords are deliberately handled with Python's standard library only so
    the local personal-account mode does not add another runtime dependency.
    The iteration count and random salt are stored with the digest, allowing a
    future cost increase without invalidating existing accounts.
    """

    if not isinstance(password, str) or not password:
        raise ValueError("Password is required")
    if iterations < 100_000:
        raise ValueError("Password iteration count is too low")
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return "$".join(
        (
            PASSWORD_SCHEME,
            str(iterations),
            _b64encode(salt),
            _b64encode(digest),
        )
    )


def verify_password(password: str, encoded: str | None) -> bool:
    """Verify a PBKDF2 password hash using a constant-time comparison."""

    if not isinstance(password, str) or not isinstance(encoded, str):
        return False
    try:
        scheme, iteration_text, salt_text, digest_text = encoded.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        iterations = int(iteration_text)
        if iterations < 100_000 or iterations > 10_000_000:
            return False
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError, UnicodeDecodeError):
        return False


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_state(payload: dict[str, str], secret: str) -> str:
    """Create a compact HMAC protected OIDC transaction cookie value.

    The cookie contains only short-lived random values.  It is not a general
    purpose session token and is rejected if its signature or JSON structure is
    invalid.
    """

    encoded = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signature = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64encode(signature)}"


def verify_state(value: str, secret: str, *, max_age_seconds: int = 600) -> dict[str, str] | None:
    try:
        encoded, signature = value.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(signature), expected):
            return None
        payload = json.loads(_b64decode(encoded))
        if not isinstance(payload, dict):
            return None
        issued_at = int(payload.get("iat", "0"))
        if issued_at <= 0 or abs(int(utcnow().timestamp()) - issued_at) > max_age_seconds:
            return None
        if not all(isinstance(payload.get(key), str) and payload[key] for key in ("state", "nonce", "verifier")):
            return None
        return {key: str(value) for key, value in payload.items()}
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return None
