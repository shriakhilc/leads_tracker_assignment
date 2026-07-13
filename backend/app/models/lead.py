from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class LeadState(str, enum.Enum):
    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = uuid_pk()
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False, index=True)

    resume_key: Mapped[str] = mapped_column(String, nullable=False)
    resume_filename: Mapped[str] = mapped_column(String, nullable=False)
    resume_content_type: Mapped[str] = mapped_column(String, nullable=False)

    state: Mapped[LeadState] = mapped_column(
        SAEnum(LeadState, name="lead_state"),
        nullable=False,
        default=LeadState.PENDING,
        index=True,
    )

    __table_args__ = (
        Index("ix_leads_created_at", "created_at"),
    )
