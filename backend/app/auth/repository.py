"""Database access for authentication and organization membership."""

from __future__ import annotations

import ipaddress
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.auth.models import (
    Invitation,
    MembershipRole,
    Organization,
    OrganizationMembership,
    Permission,
    Role,
    RolePermission,
    SessionRecord,
    UserAccount,
)
from app.auth.security import (
    hash_password,
    new_token,
    token_digest,
    utcnow,
    verify_password,
)


# Personal accounts are not tenants.  These are the minimum read/calculation
# capabilities needed by the decision tools and assistant.  Organization and
# member-management permissions are intentionally absent.
PERSONAL_ACCOUNT_PERMISSIONS = frozenset(
    {
        "policy.read",
        "evidence.read",
        "classification.read",
        "calculation.run",
        "calculation.read",
        "project.read",
        "bom.read",
        "assistant.chat",
        "assistant.upload",
        "assistant.web_search",
        "conversation.read_own",
        "conversation.archive",
    }
)


@dataclass(frozen=True)
class SessionContext:
    record: SessionRecord
    user: UserAccount
    membership: OrganizationMembership | None
    organization: Organization | None


def personal_permissions() -> set[str]:
    """Return a copy so request handlers cannot mutate the policy constant."""

    return set(PERSONAL_ACCOUNT_PERMISSIONS)


def get_session_context(db: Session, raw_token: str | None) -> SessionContext | None:
    if not raw_token:
        return None
    record = db.scalar(
        select(SessionRecord).where(SessionRecord.session_token_hash == token_digest(raw_token))
    )
    now = utcnow()
    if record is None or record.revoked_at is not None or record.expires_at <= now:
        return None
    user = db.get(UserAccount, record.user_id)
    if user is None or user.status != "ACTIVE":
        return None

    membership = None
    organization = None
    if record.current_organization_id:
        organization = db.get(Organization, record.current_organization_id)
        if organization is not None:
            membership = db.scalar(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == organization.organization_id,
                    OrganizationMembership.user_id == user.user_id,
                    OrganizationMembership.membership_status == "ACTIVE",
                )
            )
            if membership is None:
                organization = None
    if membership is None:
        membership, organization = first_membership(db, user.user_id)
    record.last_seen_at = now
    return SessionContext(record, user, membership, organization)


def first_membership(
    db: Session, user_id: uuid.UUID
) -> tuple[OrganizationMembership | None, Organization | None]:
    row = db.execute(
        select(OrganizationMembership, Organization)
        .join(Organization, Organization.organization_id == OrganizationMembership.organization_id)
        .where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.membership_status == "ACTIVE",
            Organization.status == "ACTIVE",
        )
        .order_by(OrganizationMembership.created_at.asc())
    ).first()
    return (row[0], row[1]) if row else (None, None)


def permissions_for_membership(db: Session, membership_id: uuid.UUID | None) -> set[str]:
    if membership_id is None:
        return set()
    rows = db.execute(
        select(Permission.permission_key)
        .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
        .join(Role, Role.role_id == RolePermission.role_id)
        .join(MembershipRole, MembershipRole.role_id == Role.role_id)
        .where(MembershipRole.membership_id == membership_id)
    ).all()
    return {str(row[0]) for row in rows}


def permissions_for_context(db: Session, context: SessionContext) -> set[str]:
    """Resolve permissions for either an organization or a personal session."""

    if context.membership is None:
        return personal_permissions()
    return permissions_for_membership(db, context.membership.membership_id)


def roles_for_membership(db: Session, membership_id: uuid.UUID | None) -> list[str]:
    if membership_id is None:
        return []
    rows = db.execute(
        select(Role.role_key)
        .join(MembershipRole, MembershipRole.role_id == Role.role_id)
        .where(MembershipRole.membership_id == membership_id)
        .order_by(Role.role_key.asc())
    ).all()
    return [str(row[0]) for row in rows]


def upsert_oidc_user(
    db: Session,
    *,
    identity_provider: str,
    external_subject: str,
    email: str | None,
    display_name: str | None,
    email_verified: bool = False,
) -> UserAccount:
    user = db.scalar(
        select(UserAccount).where(
            UserAccount.identity_provider == identity_provider,
            UserAccount.external_subject == external_subject,
        )
    )
    now = utcnow()
    if user is None:
        user = UserAccount(
            identity_provider=identity_provider,
            external_subject=external_subject,
            email=email,
            display_name=display_name,
            status="ACTIVE",
            email_verified=email_verified,
            created_at=now,
            updated_at=now,
            last_login_at=now,
        )
        db.add(user)
        db.flush()
    else:
        user.email = email or user.email
        user.display_name = display_name or user.display_name
        user.email_verified = email_verified or user.email_verified
        user.last_login_at = now
        user.updated_at = now
    return user


def get_user_by_email(db: Session, email: str) -> UserAccount | None:
    """Find a non-deleted account by normalized email, case-insensitively."""

    normalized = email.strip().lower()
    return db.scalar(
        select(UserAccount).where(
            func.lower(UserAccount.email) == normalized,
            UserAccount.status != "DELETED",
        )
    )


def create_personal_user(
    db: Session,
    *,
    email: str,
    password: str,
    display_name: str | None = None,
) -> UserAccount:
    """Create one standalone personal account with a PBKDF2 password hash."""

    normalized = email.strip().lower()
    if get_user_by_email(db, normalized) is not None:
        raise ValueError("An account with this email already exists")
    now = utcnow()
    user = UserAccount(
        identity_provider="personal",
        external_subject=None,
        email=normalized,
        display_name=(display_name or normalized.split("@", 1)[0]).strip()[:200],
        password_hash=hash_password(password),
        password_updated_at=now,
        status="ACTIVE",
        email_verified=False,
        created_at=now,
        updated_at=now,
        last_login_at=None,
    )
    db.add(user)
    db.flush()
    return user


def authenticate_personal_user(
    db: Session, *, email: str, password: str
) -> UserAccount | None:
    """Return an active personal account when credentials are valid."""

    user = get_user_by_email(db, email)
    if user is None or user.identity_provider != "personal" or user.status != "ACTIVE":
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = utcnow()
    user.updated_at = utcnow()
    return user


def get_or_create_organization(
    db: Session, organization_key: str, organization_name: str | None = None
) -> Organization:
    org = db.scalar(select(Organization).where(Organization.organization_key == organization_key))
    if org is not None:
        return org
    now = utcnow()
    org = Organization(
        organization_key=organization_key,
        organization_name=organization_name or organization_key,
        status="ACTIVE",
        created_at=now,
        updated_at=now,
    )
    db.add(org)
    db.flush()
    return org


def ensure_membership(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    default_role: str = "org_admin",
) -> OrganizationMembership:
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    if membership is None:
        now = utcnow()
        membership = OrganizationMembership(
            user_id=user_id,
            organization_id=organization_id,
            membership_status="ACTIVE",
            joined_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(membership)
        db.flush()
    if not db.scalar(
        select(MembershipRole).where(MembershipRole.membership_id == membership.membership_id)
    ):
        role = db.scalar(select(Role).where(Role.role_key == default_role))
        if role is not None:
            db.add(MembershipRole(membership_id=membership.membership_id, role_id=role.role_id))
    return membership


def create_session(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    max_age_seconds: int,
    auth_provider: str = "local",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str, SessionRecord]:
    raw_token = new_token(48)
    csrf_token = new_token(32)
    now = utcnow()
    normalized_ip: str | None = None
    if ip_address:
        try:
            normalized_ip = str(ipaddress.ip_address(ip_address))
        except ValueError:
            # ASGI test clients and some reverse proxies use labels such as
            # ``testclient``.  The migration deliberately uses PostgreSQL
            # inet, so never send an unvalidated host string to that column.
            normalized_ip = None
    record = SessionRecord(
        user_id=user_id,
        session_token_hash=token_digest(raw_token),
        auth_provider=auth_provider,
        current_organization_id=organization_id,
        expires_at=now + timedelta(seconds=max_age_seconds),
        created_at=now,
        last_seen_at=now,
        ip_address=normalized_ip,
        user_agent=user_agent,
    )
    db.add(record)
    db.flush()
    return raw_token, csrf_token, record


def revoke_session(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    db.execute(
        update(SessionRecord)
        .where(
            SessionRecord.session_token_hash == token_digest(raw_token),
            SessionRecord.revoked_at.is_(None),
        )
        .values(revoked_at=utcnow())
    )


def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(SessionRecord)
        .where(SessionRecord.user_id == user_id, SessionRecord.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def list_user_organizations(
    db: Session, user_id: uuid.UUID
) -> list[tuple[OrganizationMembership, Organization]]:
    return list(
        db.execute(
            select(OrganizationMembership, Organization)
            .join(Organization, Organization.organization_id == OrganizationMembership.organization_id)
            .where(OrganizationMembership.user_id == user_id)
            .order_by(Organization.organization_name.asc())
        ).all()
    )


def get_membership(
    db: Session, organization_id: uuid.UUID, membership_id: uuid.UUID
) -> OrganizationMembership | None:
    return db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.membership_id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        )
    )


def list_members(db: Session, organization_id: uuid.UUID) -> list[dict[str, object]]:
    rows = db.execute(
        select(OrganizationMembership, UserAccount)
        .join(UserAccount, UserAccount.user_id == OrganizationMembership.user_id)
        .where(OrganizationMembership.organization_id == organization_id)
        .order_by(UserAccount.email.asc())
    ).all()
    return [
        {
            "membership_id": membership.membership_id,
            "user_id": user.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "status": membership.membership_status,
            "role_codes": roles_for_membership(db, membership.membership_id),
        }
        for membership, user in rows
    ]


def set_membership_roles(
    db: Session, membership: OrganizationMembership, role_codes: list[str]
) -> None:
    normalized = sorted({code.strip().lower() for code in role_codes if code.strip()})
    roles = list(db.scalars(select(Role).where(Role.role_key.in_(normalized))))
    found = {role.role_key for role in roles}
    missing = sorted(set(normalized) - found)
    if missing:
        raise ValueError(f"Unknown role(s): {', '.join(missing)}")
    db.execute(
        delete(MembershipRole).where(MembershipRole.membership_id == membership.membership_id)
    )
    for role in roles:
        db.add(MembershipRole(membership_id=membership.membership_id, role_id=role.role_id))
    membership.updated_at = utcnow()


def create_invitation(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email: str,
    role_code: str,
    invited_by_user_id: uuid.UUID,
    expires_in_days: int,
) -> tuple[Invitation, str]:
    role_code = role_code.strip().lower()
    role = db.scalar(select(Role).where(Role.role_key == role_code))
    if role is None:
        raise ValueError(f"Unknown role: {role_code}")
    raw_token = new_token(32)
    now = utcnow()
    invitation = Invitation(
        organization_id=organization_id,
        email=email.lower(),
        invitation_token_hash=token_digest(raw_token),
        invited_by=invited_by_user_id,
        role_id=role.role_id,
        invitation_status="PENDING",
        expires_at=now + timedelta(days=expires_in_days),
        created_at=now,
    )
    db.add(invitation)
    db.flush()
    return invitation, raw_token
