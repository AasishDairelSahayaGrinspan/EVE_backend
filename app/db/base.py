"""Declarative base + timestamp mixin shared by all models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Uuid as GenericUuid


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=_utcnow,
        default=_utcnow,
        nullable=False,
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    # Generic UUID works on Postgres (native) and SQLite (char) so tests stay portable.
    return mapped_column(GenericUuid, primary_key=True, default=uuid.uuid4)
