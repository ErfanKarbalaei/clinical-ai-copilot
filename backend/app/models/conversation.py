"""Conversation — a persisted clinical-chat conversation with its messages.

Task 15 persistence layer for the Task-10 clinical chat. Messages store
only role + content; the patient context is NEVER snapshotted here — it is
rebuilt live from Task 9 at message-generation time (conversation history
and patient context remain separate concepts).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import ChatRole

if TYPE_CHECKING:
    from app.models.patient import Patient


class Conversation(TimestampMixin, Base):
    """One persisted clinical-chat conversation belonging to a patient."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(
        String(300), default="گفتگوی جدید", server_default="گفتگوی جدید"
    )

    patient: Mapped[Patient] = relationship(back_populates="conversations")
    messages: Mapped[list[ConversationMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ConversationMessage.id",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} patient_id={self.patient_id} title={self.title!r}>"


class ConversationMessage(TimestampMixin, Base):
    """One message (user question or assistant answer) in a conversation."""

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[ChatRole] = mapped_column(
        SAEnum(ChatRole, name="chat_role"),
        default=ChatRole.user,
        server_default="user",
    )
    content: Mapped[str] = mapped_column(Text)

    conversation: Mapped[Conversation] = relationship(
        back_populates="messages"
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationMessage id={self.id} "
            f"conversation_id={self.conversation_id} role={self.role}>"
        )
