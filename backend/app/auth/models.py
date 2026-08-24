"""SQLAlchemy models for the Phase A/B IAM contract.

The tables are created by the database migration owned by the database workstream.
Keeping the contract here gives API code and future migrations one canonical set of
column names without making application startup create or alter tables implicitly.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# These named PostgreSQL enums are created by migration 0011.  ``create_type``
# is disabled deliberately: importing the ORM must never try to mutate the
# database schema, while binding a typed enum is required for PostgreSQL to
# accept values such as ``ACTIVE`` instead of treating them as varchar.
USER_STATUS = SAEnum(
    "ACTIVE", "SUSPENDED", "DELETED", name="user_status", schema="iam", create_type=False
)
MEMBERSHIP_STATUS = SAEnum(
    "INVITED", "ACTIVE", "SUSPENDED", "REMOVED",
    name="membership_status", schema="iam", create_type=False,
)
ROLE_SCOPE = SAEnum(
    "SYSTEM", "ORGANIZATION", name="role_scope", schema="iam", create_type=False
)
INVITATION_STATUS = SAEnum(
    "PENDING", "ACCEPTED", "REVOKED", "EXPIRED",
    name="invitation_status", schema="iam", create_type=False,
)


class UserAccount(Base):
    __tablename__ = "user_account"
    __table_args__ = {"schema": "iam"}

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    identity_provider: Mapped[str] = mapped_column(String(500), nullable=False, default="local")
    external_subject: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(200))
    # A personal account may authenticate directly with an email/password.
    # OIDC and legacy local-development identities leave this nullable.
    # The encoded PBKDF2 value never contains the clear-text password.
    password_hash: Mapped[str | None] = mapped_column(Text)
    password_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(USER_STATUS, nullable=False, default="ACTIVE")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Organization(Base):
    __tablename__ = "organization"
    __table_args__ = {"schema": "iam"}

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    organization_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    organization_name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(USER_STATUS, nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganizationMembership(Base):
    __tablename__ = "organization_membership"
    __table_args__ = {"schema": "iam"}

    membership_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.organization.organization_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.user_account.user_id", ondelete="CASCADE"), nullable=False
    )
    membership_status: Mapped[str] = mapped_column(
        MEMBERSHIP_STATUS, nullable=False, default="ACTIVE"
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.user_account.user_id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Role(Base):
    __tablename__ = "role"
    __table_args__ = {"schema": "iam"}

    role_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    role_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    role_name_cn: Mapped[str] = mapped_column(String(200), nullable=False)
    role_name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    role_scope: Mapped[str] = mapped_column(ROLE_SCOPE, nullable=False, default="ORGANIZATION")
    description: Mapped[str | None] = mapped_column(Text)
    is_system_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Permission(Base):
    __tablename__ = "permission"
    __table_args__ = {"schema": "iam"}

    permission_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    permission_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    resource_key: Mapped[str] = mapped_column(String(80), nullable=False)
    action_key: Mapped[str] = mapped_column(String(80), nullable=False)
    permission_name_cn: Mapped[str] = mapped_column(String(200), nullable=False)
    permission_name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system_permission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permission"
    __table_args__ = {"schema": "iam"}

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.role.role_id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.permission.permission_id", ondelete="CASCADE"), primary_key=True
    )


class MembershipRole(Base):
    __tablename__ = "membership_role"
    __table_args__ = {"schema": "iam"}

    membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.organization_membership.membership_id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.role.role_id", ondelete="CASCADE"), primary_key=True
    )


class SessionRecord(Base):
    __tablename__ = "session"
    __table_args__ = {"schema": "iam"}

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.user_account.user_id", ondelete="CASCADE"), nullable=False
    )
    session_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(120), nullable=False, default="local")
    current_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.organization.organization_id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)


class Invitation(Base):
    __tablename__ = "invitation"
    __table_args__ = {"schema": "iam"}

    invitation_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.organization.organization_id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    invitation_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    # Must match database/migrations/0011_iam_core.sql exactly.
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.user_account.user_id", ondelete="SET NULL")
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.role.role_id", ondelete="RESTRICT")
    )
    invitation_status: Mapped[str] = mapped_column(
        INVITATION_STATUS, nullable=False, default="PENDING"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iam.user_account.user_id", ondelete="SET NULL")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
