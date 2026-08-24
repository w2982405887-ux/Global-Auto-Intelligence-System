"""Durable, account-owned assistant conversation history.

The assistant API intentionally keeps its existing response shapes.  This
module is the persistence boundary behind those endpoints: every lookup takes
the current ``user_id`` and therefore cannot accidentally expose another
account's transcript.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Uuid, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AssistantConversation(Base):
    __tablename__ = "conversation"
    __table_args__ = {"schema": "assistant"}

    conversation_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("iam.user_account.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    current_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("iam.organization.organization_id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="IDLE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssistantMessage(Base):
    __tablename__ = "message"
    __table_args__ = {"schema": "assistant"}

    message_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("assistant.conversation.conversation_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON keeps this model importable in the test/runtime environments while
    # PostgreSQL stores it as jsonb through the migration's native column.
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def get_owned_conversation(
    db: Session,
    conversation_id: str,
    user_id: uuid.UUID,
) -> AssistantConversation | None:
    """Return a conversation only when it belongs to ``user_id``."""

    return db.scalar(
        select(AssistantConversation).where(
            AssistantConversation.conversation_id == conversation_id,
            AssistantConversation.user_id == user_id,
        )
    )


def get_conversation(db: Session, conversation_id: str) -> AssistantConversation | None:
    """Find by ID without exposing the row to an API caller."""

    return db.get(AssistantConversation, conversation_id)


def create_conversation(
    db: Session,
    *,
    conversation_id: str,
    user_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    title: str,
) -> AssistantConversation:
    now = utcnow()
    conversation = AssistantConversation(
        conversation_id=conversation_id,
        user_id=user_id,
        current_organization_id=organization_id,
        title=(title.strip() or conversation_id[:8])[:500],
        status="IDLE",
        created_at=now,
        updated_at=now,
    )
    db.add(conversation)
    db.flush()
    return conversation


def append_message(
    db: Session,
    *,
    conversation: AssistantConversation,
    role: str,
    content: str,
    tool_calls: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AssistantMessage:
    text = content.strip()
    if not text:
        raise ValueError("assistant message content cannot be empty")
    item = AssistantMessage(
        conversation_id=conversation.conversation_id,
        role=role,
        content=text,
        tool_calls=tool_calls or [],
        message_metadata=metadata or {},
        created_at=utcnow(),
    )
    db.add(item)
    conversation.updated_at = item.created_at
    db.flush()
    return item


def list_owned_conversations(
    db: Session, user_id: uuid.UUID
) -> list[AssistantConversation]:
    return list(
        db.scalars(
            select(AssistantConversation)
            .where(AssistantConversation.user_id == user_id)
            .order_by(AssistantConversation.updated_at.desc())
        )
    )


def list_messages(
    db: Session, conversation: AssistantConversation
) -> list[AssistantMessage]:
    return list(
        db.scalars(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conversation.conversation_id)
            .order_by(AssistantMessage.created_at.asc(), AssistantMessage.message_id.asc())
        )
    )


def serialize_message(message: AssistantMessage) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(message.message_id),
        "role": message.role,
        "content": message.content,
        "timestamp": message.created_at.isoformat(),
    }
    if message.tool_calls:
        result["toolCalls"] = message.tool_calls
    return result


def langchain_messages(
    db: Session, conversation: AssistantConversation
) -> list[Any]:
    """Convert persisted user/assistant messages to LangChain messages."""

    from langchain_core.messages import AIMessage, HumanMessage

    converted: list[Any] = []
    for message in list_messages(db, conversation):
        if message.role == "user":
            converted.append(HumanMessage(content=message.content))
        elif message.role == "assistant":
            converted.append(AIMessage(content=message.content))
    return converted
