from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import Lead
from app.repositories.users_repo import UsersRepository
from app.services.assignment.base import AssignmentError


class SingleAttorneyStrategy:
    """Current implementation: route every lead to the one seeded attorney."""

    def __init__(self, db: Session):
        self._users = UsersRepository(db)

    def assign(self, lead: Lead) -> uuid.UUID:
        attorney = self._users.first_attorney()
        if attorney is None:
            raise AssignmentError("No attorney available to assign the lead to.")
        return attorney.id
