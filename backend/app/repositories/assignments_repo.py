from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LeadAssignment, User
from app.models.assignment import ASSIGNED_BY_SYSTEM


class AssignmentsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_active(
        self, *, lead_id: uuid.UUID, attorney_id: uuid.UUID, assigned_by: str = ASSIGNED_BY_SYSTEM
    ) -> LeadAssignment:
        assignment = LeadAssignment(
            lead_id=lead_id, attorney_id=attorney_id, assigned_by=assigned_by, active=True
        )
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def active_for_lead(self, lead_id: uuid.UUID) -> LeadAssignment | None:
        return self.db.execute(
            select(LeadAssignment)
            .where(LeadAssignment.lead_id == lead_id)
            .where(LeadAssignment.active.is_(True))
        ).scalar_one_or_none()

    def active_attorney_for_lead(self, lead_id: uuid.UUID) -> User | None:
        return self.db.execute(
            select(User)
            .join(LeadAssignment, LeadAssignment.attorney_id == User.id)
            .where(LeadAssignment.lead_id == lead_id)
            .where(LeadAssignment.active.is_(True))
        ).scalar_one_or_none()

    def active_attorneys_for_leads(self, lead_ids: list[uuid.UUID]) -> dict[uuid.UUID, User]:
        """Batch lookup to avoid N+1 when listing leads."""
        if not lead_ids:
            return {}
        rows = self.db.execute(
            select(LeadAssignment.lead_id, User)
            .join(User, LeadAssignment.attorney_id == User.id)
            .where(LeadAssignment.lead_id.in_(lead_ids))
            .where(LeadAssignment.active.is_(True))
        ).all()
        return {lead_id: user for lead_id, user in rows}
