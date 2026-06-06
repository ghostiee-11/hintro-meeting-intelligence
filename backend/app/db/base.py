from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def generate_uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UUIDMixin:
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
