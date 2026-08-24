"""FastAPI dependencies enforcing server-side identity, tenant and RBAC."""

from __future__ import annotations

from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.models import Organization, OrganizationMembership, UserAccount
from app.auth.repository import (
    SessionContext,
    get_session_context,
    permissions_for_context,
)
from app.auth.security import constant_time_equal
from app.core.config import get_settings
from app.db.session import get_db_session


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Session"},
    )


def _context(request: Request, db: Session) -> SessionContext:
    settings = get_settings()
    raw = request.cookies.get(settings.auth_session_cookie_name)
    context = get_session_context(db, raw)
    if context is None:
        raise _unauthorized()
    request.state.auth_context = context
    request.state.auth_session_token = raw
    return context


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
) -> UserAccount:
    return _context(request, db).user


def get_current_membership(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
) -> OrganizationMembership:
    membership = _context(request, db).membership
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active organization membership")
    return membership


def get_current_organization(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
) -> Organization:
    organization = _context(request, db).organization
    if organization is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active organization context")
    return organization


def get_auth_context(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
) -> SessionContext:
    return _context(request, db)


def require_permission(permission: str) -> Callable:
    """Return a dependency that fails closed unless the current org grants it."""

    normalized = permission.strip().lower()

    def _require(
        request: Request,
        db: Annotated[Session, Depends(get_db_session)],
    ) -> SessionContext:
        context = _context(request, db)
        # Standalone personal accounts do not have an organization membership,
        # but they may use the product's calculation and assistant features.
        # ``permissions_for_context`` returns only the explicitly allowlisted
        # personal permissions and never member/organization administration.
        permissions = permissions_for_context(db, context)
        if normalized not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {normalized}",
            )
        request.state.auth_permissions = permissions
        return context

    return _require


def require_csrf(
    request: Request,
    context: Annotated[SessionContext, Depends(get_auth_context)],
) -> None:
    """Double-submit CSRF check for cookie-authenticated state changes.

    SameSite=Lax is still set on the session cookie, but the explicit header
    check protects authenticated POST/PATCH/DELETE calls made by a browser
    from same-site navigations or a compromised same-site page.
    """

    if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return
    settings = get_settings()
    cookie_value = request.cookies.get(settings.auth_csrf_cookie_name)
    header_value = request.headers.get(settings.auth_csrf_header_name)
    if cookie_value and header_value and constant_time_equal(cookie_value, header_value):
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


CurrentUser = Annotated[UserAccount, Depends(get_current_user)]
CurrentMembership = Annotated[OrganizationMembership, Depends(get_current_membership)]
CurrentOrganization = Annotated[Organization, Depends(get_current_organization)]
