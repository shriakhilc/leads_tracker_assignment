from __future__ import annotations

import uuid
from typing import Protocol

from app.models import Lead


class AssignmentError(RuntimeError):
    """Raised when no attorney can be assigned to a lead."""


class AssignmentStrategy(Protocol):
    """Extension point for lead → attorney routing (§4).

    Swapping in real routing (round-robin, practice area, geography, load-based) touches
    only the strategy - never the router, the `leads` table, or the submission flow.
    """

    def assign(self, lead: Lead) -> uuid.UUID:
        """Return the attorney (user) id this lead should be assigned to."""
        ...
