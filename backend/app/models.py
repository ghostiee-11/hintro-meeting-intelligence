"""SQLAlchemy ORM models for the Meeting Intelligence service.

Design (see DECISIONS.md): a relational model fits the strong
meeting -> segments -> insights/action-items -> citations graph. Citations are a
first-class table so grounding is queryable and verifiable. Transcript segments
carry a pgvector embedding so semantic search needs no second datastore.
"""

import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

EMBEDDING_DIMS = 768


class MeetingStatus(enum.StrEnum):
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class ActionItemStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class InsightType(enum.StrEnum):
    SUMMARY = "SUMMARY"
    DECISION = "DECISION"
    FOLLOW_UP = "FOLLOW_UP"


class ReminderChannel(enum.StrEnum):
    TELEGRAM = "TELEGRAM"
    DISCORD = "DISCORD"


class ReminderStatus(enum.StrEnum):
    SENT = "SENT"
    FAILED = "FAILED"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    meetings: Mapped[list["Meeting"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Meeting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "meetings"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    meeting_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    participants: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, name="meeting_status"), default=MeetingStatus.CREATED, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="meetings")
    segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", order_by="TranscriptSegment.ordinal"
    )
    insights: Mapped[list["Insight"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )


class TranscriptSegment(UUIDMixin, Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (UniqueConstraint("meeting_id", "ordinal", name="uq_segment_ordinal"),)

    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    speaker: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMS), nullable=True)

    meeting: Mapped["Meeting"] = relationship(back_populates="segments")
    citations: Mapped[list["Citation"]] = relationship(back_populates="segment")


class Insight(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "insights"

    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[InsightType] = mapped_column(
        Enum(InsightType, name="insight_type"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    grounding_score: Mapped[float] = mapped_column(Float, default=0.0)

    meeting: Mapped["Meeting"] = relationship(back_populates="insights")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="insight", cascade="all, delete-orphan"
    )


class ActionItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "action_items"

    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    task: Mapped[str] = mapped_column(Text, nullable=False)
    assignee: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    status: Mapped[ActionItemStatus] = mapped_column(
        Enum(ActionItemStatus, name="action_item_status"),
        default=ActionItemStatus.PENDING,
        index=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    grounding_score: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String, default="AI")  # AI or MANUAL
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="action_items")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="action_item", cascade="all, delete-orphan"
    )
    reminders: Mapped[list["ReminderLog"]] = relationship(
        back_populates="action_item", cascade="all, delete-orphan"
    )


class Citation(UUIDMixin, Base):
    __tablename__ = "citations"

    transcript_segment_id: Mapped[str | None] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True
    )
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    segment_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    insight_id: Mapped[str | None] = mapped_column(
        ForeignKey("insights.id", ondelete="CASCADE"), index=True, nullable=True
    )
    action_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("action_items.id", ondelete="CASCADE"), index=True, nullable=True
    )

    segment: Mapped["TranscriptSegment"] = relationship(back_populates="citations")
    insight: Mapped["Insight"] = relationship(back_populates="citations")
    action_item: Mapped["ActionItem"] = relationship(back_populates="citations")


class ReminderLog(UUIDMixin, Base):
    __tablename__ = "reminder_logs"

    action_item_id: Mapped[str] = mapped_column(
        ForeignKey("action_items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel: Mapped[ReminderChannel] = mapped_column(
        Enum(ReminderChannel, name="reminder_channel"), nullable=False
    )
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, name="reminder_status"), nullable=False
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str] = mapped_column(String, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    action_item: Mapped["ActionItem"] = relationship(back_populates="reminders")
