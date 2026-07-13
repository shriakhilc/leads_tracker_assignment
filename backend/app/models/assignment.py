from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk

ASSIGNED_BY_SYSTEM = "SYSTEM"


class LeadAssignment(Base):
    """Maps a lead to its attorney. Invariant: exactly one active row per lead."""

    __tablename__ = "lead_assignments"

    id: Mapped[uuid.UUID] = uuid_pk()
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attorney_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # "SYSTEM" for auto-routing, or a user id string for manual reassignment.
    assigned_by: Mapped[str] = mapped_column(String, nullable=False, default=ASSIGNED_BY_SYSTEM)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        # Enforce "exactly one active assignment per lead" at the DB level.
        Index(
            "uq_lead_assignments_one_active",
            "lead_id",
            unique=True,
            postgresql_where="active",
        ),
    )
