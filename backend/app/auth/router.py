"""Stage A+B authentication, organization and RBAC HTTP endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    CurrentUser,
    get_auth_context,
    require_csrf,
    require_permission,
)
from app.auth.oidc import (
    OIDCError,
    authorization_url,
    discover,
    exchange_code,
    userinfo,
    validate_id_token,
)
from app.auth.repository import (
    SessionContext,
    authenticate_personal_user,
    create_invitation,
    create_personal_user,
    create_session,
    ensure_membership,
    get_or_create_organization,
    get_session_context,
    list_members,
    list_user_organizations,
    permissions_for_context,
    revoke_all_sessions,
    revoke_session,
    roles_for_membership,
    set_membership_roles,
    upsert_oidc_user,
)
from app.auth.schemas import (
    AuthMeResponse,
    InvitationCreate,
    InvitationResponse,
    LocalLoginRequest,
    MemberRoleUpdate,
    OrganizationSummary,
    PermissionResponse,
    PersonalLoginRequest,
    PersonalRegisterRequest,
    UserSummary,
)
from app.auth.security import new_token, sign_state, utcnow, verify_state
from app.core.config import get_settings
from app.db.session import get_db_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
organization_router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])

OIDC_STATE_COOKIE = "gais_oidc_state"


def _ensure_auth_secret() -> str:
    settings = get_settings()
    secret = settings.auth_secret_key
    if not secret or secret == "change-me-in-production":
        raise HTTPException(status_code=503, detail="Authentication secret is not configured")
    return secret


def _cookie_secure() -> bool:
    settings = get_settings()
    if settings.environment.lower() in {"production", "prod", "staging"}:
        return True
    return settings.auth_cookie_secure


def _set_session_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    settings = get_settings()
    common = {
        "secure": _cookie_secure(),
        "httponly": True,
        "samesite": settings.auth_cookie_samesite.lower(),
        "domain": settings.auth_cookie_domain,
        "path": "/",
        "max_age": settings.auth_session_max_age_seconds,
    }
    response.set_cookie(settings.auth_session_cookie_name, session_token, **common)
    # The CSRF token is intentionally readable by the first-party frontend.
    response.set_cookie(
        settings.auth_csrf_cookie_name,
        csrf_token,
        secure=common["secure"],
        httponly=False,
        samesite=common["samesite"],
        domain=common["domain"],
        path="/",
        max_age=common["max_age"],
    )


def _clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    for name in (settings.auth_session_cookie_name, settings.auth_csrf_cookie_name, OIDC_STATE_COOKIE):
        response.delete_cookie(name, domain=settings.auth_cookie_domain, path="/")


def _user_summary(user) -> UserSummary:
    return UserSummary(
        user_id=user.user_id,
        id=user.user_id,
        email=user.email,
        full_name=user.display_name,
        display_name=user.display_name,
        issuer=user.identity_provider,
        subject=user.external_subject or "",
        status=str(user.status),
    )


def _org_summary(db: Session, membership, organization) -> OrganizationSummary:
    return OrganizationSummary(
        organization_id=organization.organization_id,
        id=organization.organization_id,
        organization_code=organization.organization_key,
        code=organization.organization_key,
        name=organization.organization_name,
        display_name=organization.organization_name,
        status=str(organization.status),
        membership_id=membership.membership_id,
        membership_status=str(membership.membership_status),
        role=(roles_for_membership(db, membership.membership_id) or [None])[0],
        role_codes=roles_for_membership(db, membership.membership_id),
    )


def _organizations(db: Session, user_id: uuid.UUID) -> list[OrganizationSummary]:
    return [_org_summary(db, membership, organization) for membership, organization in list_user_organizations(db, user_id)]


def _me(db: Session, context: SessionContext, csrf_token: str) -> AuthMeResponse:
    active = (
        _org_summary(db, context.membership, context.organization)
        if context.membership is not None and context.organization is not None
        else None
    )
    return AuthMeResponse(
        authenticated=True,
        user=_user_summary(context.user),
        active_organization=active,
        current_organization=active,
        organizations=_organizations(db, context.user.user_id),
        permissions=sorted(permissions_for_context(db, context)),
        csrf_token=csrf_token,
        auth_config={
            "personal_login_enabled": get_settings().auth_personal_enabled,
            "oidc_enabled": get_settings().auth_oidc_enabled,
            "dev_login_enabled": get_settings().auth_local_dev_enabled,
        },
    )


def _safe_return_to(value: str | None) -> str:
    """Allow only a local path; never reflect an arbitrary redirect URL."""
    if not value:
        return "/"
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


@router.get("/config", name="auth_config")
def auth_config() -> dict[str, object]:
    settings = get_settings()
    return {
        "personal_login_enabled": settings.auth_personal_enabled,
        "personal_login_label": "个人账号登录" if settings.auth_personal_enabled else None,
        "oidc_enabled": settings.auth_oidc_enabled,
        "oidc_provider_name": settings.auth_oidc_issuer_url or None,
        "dev_login_enabled": settings.auth_local_dev_enabled,
        "dev_login_label": "本地开发登录" if settings.auth_local_dev_enabled else None,
    }


def _require_personal_login() -> None:
    if not get_settings().auth_personal_enabled:
        raise HTTPException(status_code=404, detail="Personal account login is disabled")


def _finish_personal_login(
    *,
    user,
    request: Request,
    response: Response,
    db: Session,
) -> dict[str, object]:
    settings = get_settings()
    raw_session, csrf_token, _ = create_session(
        db,
        user_id=user.user_id,
        organization_id=None,
        max_age_seconds=settings.auth_session_max_age_seconds,
        auth_provider="personal",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    _set_session_cookies(response, raw_session, csrf_token)
    context = get_session_context(db, raw_session)
    if context is None:
        raise HTTPException(status_code=500, detail="Session creation failed")
    return _me(db, context, csrf_token).model_dump(mode="json")


@router.post("/register", name="personal_register")
def personal_register(
    payload: PersonalRegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
):
    """Register a standalone account; no organization is created or required."""

    _require_personal_login()
    try:
        user = create_personal_user(
            db,
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
        result = _finish_personal_login(
            user=user, request=request, response=response, db=db
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        # Do not leak whether a race won the unique-email constraint.
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from exc
    return result


@router.post("/login", name="personal_login")
def personal_login(
    payload: PersonalLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
):
    """Authenticate a personal account and issue an opaque server session."""

    _require_personal_login()
    user = authenticate_personal_user(
        db, email=payload.email, password=payload.password
    )
    if user is None:
        # Keep the response identical for unknown emails and wrong passwords.
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _finish_personal_login(
        user=user, request=request, response=response, db=db
    )


@router.get("/oidc/start", name="oidc_start")
async def oidc_start(return_to: str = "/"):
    settings = get_settings()
    if not settings.auth_oidc_enabled:
        raise HTTPException(status_code=404, detail="OIDC login is disabled")
    if not settings.auth_oidc_client_id or not settings.auth_oidc_redirect_uri:
        raise HTTPException(status_code=503, detail="OIDC client is not configured")
    secret = _ensure_auth_secret()
    try:
        configuration = await discover(settings)
    except OIDCError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    state = new_token(32)
    nonce = new_token(32)
    verifier = new_token(48)
    signed = sign_state(
        {
            "state": state,
            "nonce": nonce,
            "verifier": verifier,
            "return_to": _safe_return_to(return_to),
            "iat": str(int(utcnow().timestamp())),
        },
        secret,
    )
    redirect = RedirectResponse(
        authorization_url(configuration, settings, state=state, nonce=nonce, verifier=verifier),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    redirect.set_cookie(
        OIDC_STATE_COOKIE,
        signed,
        secure=_cookie_secure(),
        httponly=True,
        samesite="lax",
        domain=settings.auth_cookie_domain,
        path="/",
        max_age=settings.auth_oidc_state_max_age_seconds,
    )
    return redirect


@router.get("/oidc/callback", name="oidc_callback")
async def oidc_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    settings = get_settings()
    if not settings.auth_oidc_enabled:
        raise HTTPException(status_code=404, detail="OIDC login is disabled")
    if error or not code or not state:
        raise HTTPException(status_code=400, detail="OIDC authorization was not completed")
    transaction = verify_state(
        request.cookies.get(OIDC_STATE_COOKIE, ""),
        _ensure_auth_secret(),
        max_age_seconds=settings.auth_oidc_state_max_age_seconds,
    )
    if transaction is None or transaction.get("state") != state:
        raise HTTPException(status_code=400, detail="Invalid or expired OIDC state")
    try:
        configuration = await discover(settings)
        token_data = await exchange_code(configuration, settings, code=code, verifier=transaction["verifier"])
        claims = await validate_id_token(
            configuration,
            settings,
            str(token_data["id_token"]),
            expected_nonce=transaction["nonce"],
        )
        extra = await userinfo(configuration, str(token_data.get("access_token", "")))
    except OIDCError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    subject = str(claims["sub"])
    email = str(claims.get("email") or extra.get("email") or "") or None
    display_name = str(
        claims.get("name") or extra.get("name") or claims.get("preferred_username") or email or subject
    )
    user = upsert_oidc_user(
        db,
        identity_provider=configuration.issuer,
        external_subject=subject,
        email=email,
        display_name=display_name,
        email_verified=bool(claims.get("email_verified") or extra.get("email_verified")),
    )
    org = None
    if settings.auth_default_organization_key:
        org = get_or_create_organization(
            db,
            settings.auth_default_organization_key,
            settings.auth_default_organization_name or settings.auth_default_organization_key,
        )
        if not list_user_organizations(db, user.user_id):
            ensure_membership(db, user_id=user.user_id, organization_id=org.organization_id)
    raw_session, csrf_token, _ = create_session(
        db,
        user_id=user.user_id,
        organization_id=org.organization_id if org else None,
        max_age_seconds=settings.auth_session_max_age_seconds,
        auth_provider=configuration.issuer,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    target = _safe_return_to(transaction.get("return_to"))
    if target == "/":
        target = settings.auth_oidc_success_redirect_uri
    redirect = RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookies(redirect, raw_session, csrf_token)
    redirect.delete_cookie(OIDC_STATE_COOKIE, domain=settings.auth_cookie_domain, path="/")
    return redirect


@router.post("/dev/login", name="dev_login")
@router.post("/local-login", name="local_login")
def local_login(
    payload: LocalLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
):
    settings = get_settings()
    # A local login fabricates an identity and (for the development fixture)
    # grants membership in the configured local organization.  It must never
    # be possible to enable that escape hatch in a deployed environment by
    # setting only the feature flag.
    if settings.environment.lower() in {"production", "prod", "staging"}:
        raise HTTPException(status_code=404, detail="Local development login is unavailable in this environment")
    if not settings.auth_local_dev_enabled:
        raise HTTPException(status_code=404, detail="Local development login is disabled")
    organization_key = payload.organization_code or settings.auth_local_dev_organization_key
    if not organization_key:
        raise HTTPException(status_code=503, detail="Local development organization is not configured")
    organization = get_or_create_organization(
        db, organization_key, settings.auth_local_dev_organization_name or organization_key
    )
    user = upsert_oidc_user(
        db,
        identity_provider="local",
        external_subject=payload.email,
        email=payload.email,
        display_name=payload.display_name or payload.email,
        email_verified=True,
    )
    ensure_membership(db, user_id=user.user_id, organization_id=organization.organization_id)
    raw_session, csrf_token, _ = create_session(
        db,
        user_id=user.user_id,
        organization_id=organization.organization_id,
        max_age_seconds=settings.auth_session_max_age_seconds,
        auth_provider="local",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    _set_session_cookies(response, raw_session, csrf_token)
    context = get_session_context(db, raw_session)
    if context is None:
        raise HTTPException(status_code=500, detail="Session creation failed")
    return _me(db, context, csrf_token).model_dump(mode="json")


@router.get("/me", response_model=AuthMeResponse, name="auth_me")
def auth_me(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
) -> AuthMeResponse:
    context = get_auth_context(request, db)
    csrf = request.cookies.get(get_settings().auth_csrf_cookie_name, "")
    return _me(db, context, csrf)


@router.post("/logout", name="auth_logout")
def logout(
    request: Request,
    response: Response,
    _: Annotated[None, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db_session)],
):
    revoke_session(db, request.cookies.get(get_settings().auth_session_cookie_name))
    db.commit()
    _clear_session_cookies(response)
    return {"status": "ok"}


@router.post("/revoke-all", name="auth_revoke_all")
def revoke_all(
    response: Response,
    context: Annotated[SessionContext, Depends(get_auth_context)],
    _: Annotated[None, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db_session)],
):
    revoke_all_sessions(db, context.user.user_id)
    db.commit()
    _clear_session_cookies(response)
    return {"status": "ok"}


@organization_router.get("", name="list_organizations")
def organizations(user: CurrentUser, db: Annotated[Session, Depends(get_db_session)]):
    return {"items": [item.model_dump(mode="json") for item in _organizations(db, user.user_id)]}


@organization_router.post("/{organization_id}/switch", name="switch_organization")
def switch_organization(
    organization_id: uuid.UUID,
    request: Request,
    _: Annotated[None, Depends(require_csrf)],
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db_session)],
):
    context = get_auth_context(request, db)
    if context.user.user_id != user.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    membership, organization = next(
        (
            (membership, organization)
            for membership, organization in list_user_organizations(db, user.user_id)
            if organization.organization_id == organization_id and membership.membership_status == "ACTIVE"
        ),
        (None, None),
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="Organization access denied")
    context.record.current_organization_id = organization_id
    db.commit()
    if organization is None or membership is None:
        raise HTTPException(status_code=403, detail="Organization access denied")
    active = _org_summary(db, membership, organization)
    return {"status": "ok", "active_organization": active.model_dump(mode="json")}


@organization_router.get("/{organization_id}/members", name="list_organization_members")
def organization_members(
    organization_id: uuid.UUID,
    context: Annotated[SessionContext, Depends(require_permission("member.read"))],
    db: Annotated[Session, Depends(get_db_session)],
):
    if context.organization is None or context.organization.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Organization access denied")
    return {"organization_id": str(organization_id), "items": list_members(db, organization_id)}


@organization_router.post("/{organization_id}/members/invitations", name="invite_member")
def invite_member(
    organization_id: uuid.UUID,
    payload: InvitationCreate,
    user: CurrentUser,
    context: Annotated[SessionContext, Depends(require_permission("member.manage"))],
    __: Annotated[None, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db_session)],
):
    if context.organization is None or context.organization.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Organization access denied")
    try:
        invitation, raw_token = create_invitation(
            db,
            organization_id=organization_id,
            email=payload.email,
            role_code=payload.role_code,
            invited_by_user_id=user.user_id,
            expires_in_days=payload.expires_in_days,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "invitation": InvitationResponse(
            id=invitation.invitation_id,
            email=invitation.email,
            role_code=payload.role_code.lower(),
            status=str(invitation.invitation_status),
            expires_at=invitation.expires_at,
        ),
        # The raw token is returned once so an email service can be integrated
        # later; only the hash is persisted in PostgreSQL.
        "invitation_token": raw_token,
    }


@organization_router.patch("/{organization_id}/members/{membership_id}", name="update_member")
def update_member(
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    payload: MemberRoleUpdate,
    context: Annotated[SessionContext, Depends(require_permission("role.manage"))],
    __: Annotated[None, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db_session)],
):
    if context.organization is None or context.organization.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Organization access denied")
    from app.auth.repository import get_membership

    membership = get_membership(db, organization_id, membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found in organization")
    try:
        set_membership_roles(db, membership, payload.role_codes)
        if payload.status:
            membership.membership_status = payload.status
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok", "membership_id": str(membership.membership_id), "role_codes": payload.role_codes}


@router.get("/me/permissions", response_model=PermissionResponse, name="my_permissions")
def my_permissions(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
):
    context = get_auth_context(request, db)
    return PermissionResponse(
        user_id=context.user.user_id,
        organization_id=context.organization.organization_id if context.organization else None,
        permissions=sorted(permissions_for_context(db, context)),
    )
