"""Public request/response contracts for IAM endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocalLoginRequest(BaseModel):
    # The frontend may intentionally use the server's local-dev identity
    # without sending a body.  Keep a deterministic, non-production default;
    # the endpoint remains unavailable unless auth_local_dev_enabled=true.
    email: str = "dev@example.local"
    display_name: str | None = Field(default=None, max_length=200)
    organization_code: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value


class PersonalRegisterRequest(BaseModel):
    """Credentials for a standalone personal account.

    Personal accounts are intentionally not tied to an organization.  The
    email is the stable account identifier and is unique case-insensitively.
    """

    email: str
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value

    @field_validator("password")
    @classmethod
    def non_blank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password cannot be blank")
        return value


class PersonalLoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value


class MemberRoleUpdate(BaseModel):
    role_codes: list[str] = Field(min_length=1, max_length=20)
    status: str | None = Field(default=None, pattern=r"^(ACTIVE|SUSPENDED)$")


class InvitationCreate(BaseModel):
    email: str
    role_code: str = Field(default="viewer", min_length=1, max_length=80)
    expires_in_days: int = Field(default=7, ge=1, le=30)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value


class OrganizationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    id: UUID | None = None
    organization_code: str | None = None
    code: str | None = None
    name: str
    display_name: str | None = None
    status: str
    membership_id: UUID | None = None
    membership_status: str | None = None
    role: str | None = None
    role_codes: list[str] = Field(default_factory=list)


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    id: UUID | None = None
    email: str | None = None
    full_name: str | None = None
    display_name: str | None = None
    issuer: str = ""
    subject: str = ""
    status: str = "ACTIVE"


class AuthMeResponse(BaseModel):
    authenticated: bool = True
    user: UserSummary | None = None
    organizations: list[OrganizationSummary] = Field(default_factory=list)
    active_organization: OrganizationSummary | None = None
    current_organization: OrganizationSummary | None = None
    permissions: list[str] = Field(default_factory=list)
    csrf_token: str = ""
    auth_config: dict[str, Any] | None = None


class PermissionResponse(BaseModel):
    user_id: UUID
    organization_id: UUID | None
    permissions: list[str]


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    role_code: str
    status: str
    expires_at: datetime
