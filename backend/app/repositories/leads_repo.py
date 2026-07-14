from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Lead, LeadAssignment, LeadState, User


class LeadsRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, lead: Lead) -> Lead:
        self.db.add(lead)
        self.db.flush()  # assigns PK / defaults without committing
        return lead

    def get(self, lead_id: uuid.UUID) -> Lead | None:
        return self.db.get(Lead, lead_id)

    def list(
        self,
        *,
        state: LeadState | None = None,
        assigned_to: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[Lead], int]:
        stmt = select(Lead)
        count_stmt = select(func.count(Lead.id))

        if state is not None:
            stmt = stmt.where(Lead.state == state)
            count_stmt = count_stmt.where(Lead.state == state)

        if assigned_to is not None:
            active_lead_ids = (
                select(LeadAssignment.lead_id)
                .where(LeadAssignment.active.is_(True))
                .where(LeadAssignment.attorney_id == assigned_to)
            )
            stmt = stmt.where(Lead.id.in_(active_lead_ids))
            count_stmt = count_stmt.where(Lead.id.in_(active_lead_ids))

        order_desc = order.lower() == "desc"

        def direction(col):
            return col.desc() if order_desc else col.asc()

        if sort == "assignee":
            # Order by the active assignment's attorney email. The unique partial index
            # guarantees at most one active assignment per lead, so this outer join
            # never fans a lead out into duplicate rows.
            stmt = (
                stmt.outerjoin(
                    LeadAssignment,
                    (LeadAssignment.lead_id == Lead.id) & (LeadAssignment.active.is_(True)),
                )
                .outerjoin(User, User.id == LeadAssignment.attorney_id)
                .order_by(direction(User.email))
            )
        elif sort == "name":
            stmt = stmt.order_by(direction(Lead.first_name), direction(Lead.last_name))
        else:
            sort_col = {
                "created_at": Lead.created_at,
                "state": Lead.state,
                "email": Lead.email,
            }.get(sort, Lead.created_at)
            stmt = stmt.order_by(direction(sort_col))

        stmt = stmt.limit(limit).offset(offset)

        items = list(self.db.execute(stmt).scalars().all())
        total = self.db.execute(count_stmt).scalar_one()
        return items, total
