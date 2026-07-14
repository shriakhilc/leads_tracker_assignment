"""Business logic for leads: submission orchestration, state machine, resume access.

Transaction boundary (§3): the lead row *and* its active assignment are written in one
transaction. Emails are scheduled by the router only after this commits.
"""
from __future__ import annotations

import io
import logging
import re
import uuid

from sqlalchemy.orm import Session

from app.adapters.storage import get_storage
from app.core.config import settings
from app.models import Lead, LeadState
from app.repositories.assignments_repo import AssignmentsRepository
from app.repositories.leads_repo import LeadsRepository
from app.schemas.lead import AssigneeOut, LeadOut
from app.services.assignment import AssignmentStrategy, SingleAttorneyStrategy
from app.services.exceptions import (
    IllegalStateTransition,
    NotFoundError,
    UploadTooLarge,
    UploadValidationError,
)

logger = logging.getLogger(__name__)

# Legal state transitions (§4.2). Centralized so future states are a one-line change.
# REACHED_OUT -> PENDING is allowed so an attorney can undo a mistaken "reached out" click.
_ALLOWED_TRANSITIONS: dict[LeadState, set[LeadState]] = {
    LeadState.PENDING: {LeadState.REACHED_OUT},
    LeadState.REACHED_OUT: {LeadState.PENDING},
}

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(name: str) -> str:
    base = (name or "resume").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    cleaned = _FILENAME_SAFE.sub("_", base).strip("._") or "resume"
    return cleaned[:200]


class LeadsService:
    def __init__(self, db: Session, strategy: AssignmentStrategy | None = None):
        self.db = db
        self.leads = LeadsRepository(db)
        self.assignments = AssignmentsRepository(db)
        self.strategy = strategy or SingleAttorneyStrategy(db)
        self.storage = get_storage()

    # --- Submission (F1–F3) ---
    def submit_lead(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        resume_bytes: bytes,
        resume_filename: str,
        resume_content_type: str,
    ) -> Lead:
        self._validate_upload(resume_content_type, len(resume_bytes))

        safe_name = _sanitize_filename(resume_filename)
        # Random, unguessable key - never trust client-supplied paths (§10).
        resume_key = f"resumes/{uuid.uuid4()}/{safe_name}"

        # 1) Upload the resume to object storage first (outside the DB txn).
        self.storage.put(resume_key, io.BytesIO(resume_bytes), resume_content_type)

        try:
            # 2) Lead + assignment in ONE transaction.
            lead = self.leads.add(
                Lead(
                    first_name=first_name.strip(),
                    last_name=last_name.strip(),
                    email=email.strip(),
                    resume_key=resume_key,
                    resume_filename=safe_name,
                    resume_content_type=resume_content_type,
                    state=LeadState.PENDING,
                )
            )
            # 3) Assign in the same transaction (attorney email later targets this assignee).
            attorney_id = self.strategy.assign(lead)
            self.assignments.create_active(lead_id=lead.id, attorney_id=attorney_id)

            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Lead submission failed; rolling back", extra={"extra": {"email": email}})
            raise

        self.db.refresh(lead)
        logger.info("Lead submitted", extra={"extra": {"lead_id": str(lead.id)}})
        return lead

    def _validate_upload(self, content_type: str, size: int) -> None:
        if size == 0:
            raise UploadValidationError("Resume file is empty.")
        if size > settings.max_upload_bytes:
            raise UploadTooLarge(
                f"Resume exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit."
            )
        if content_type not in settings.allowed_resume_content_types:
            raise UploadValidationError(
                f"Unsupported file type '{content_type}'. Allowed: PDF, DOC, DOCX."
            )

    # --- Retrieval (F4, F6) ---
    def get_lead(self, lead_id: uuid.UUID) -> Lead:
        lead = self.leads.get(lead_id)
        if lead is None:
            raise NotFoundError("Lead not found.")
        return lead

    def to_out(self, lead: Lead) -> LeadOut:
        attorney = self.assignments.active_attorney_for_lead(lead.id)
        out = LeadOut.model_validate(lead)
        if attorney is not None:
            out.assignee = AssigneeOut(
                attorney_id=attorney.id, email=attorney.email, full_name=attorney.full_name
            )
        return out

    def list_leads(
        self,
        *,
        state: LeadState | None,
        assigned_to: uuid.UUID | None,
        limit: int,
        offset: int,
        sort: str,
        order: str,
    ) -> tuple[list[LeadOut], int]:
        leads, total = self.leads.list(
            state=state, assigned_to=assigned_to, limit=limit, offset=offset, sort=sort, order=order
        )
        assignees = self.assignments.active_attorneys_for_leads([lead.id for lead in leads])
        items: list[LeadOut] = []
        for lead in leads:
            out = LeadOut.model_validate(lead)
            attorney = assignees.get(lead.id)
            if attorney is not None:
                out.assignee = AssigneeOut(
                    attorney_id=attorney.id, email=attorney.email, full_name=attorney.full_name
                )
            items.append(out)
        return items, total

    # --- State machine (F5) ---
    def transition_state(self, lead_id: uuid.UUID, target: LeadState) -> Lead:
        lead = self.get_lead(lead_id)
        if target == lead.state:
            return lead  # idempotent no-op
        if target not in _ALLOWED_TRANSITIONS.get(lead.state, set()):
            raise IllegalStateTransition(
                f"Cannot transition lead from {lead.state.value} to {target.value}."
            )
        lead.state = target
        self.db.commit()
        self.db.refresh(lead)
        logger.info(
            "Lead state changed",
            extra={"extra": {"lead_id": str(lead_id), "state": target.value}},
        )
        return lead

    # --- Resume access (F6) ---
    def resume_presigned_url(self, lead_id: uuid.UUID) -> tuple[str, int]:
        lead = self.get_lead(lead_id)
        ttl = settings.presigned_url_expire_seconds
        return self.storage.presigned_get_url(lead.resume_key, ttl), ttl

    def resume_stream(self, lead_id: uuid.UUID):
        lead = self.get_lead(lead_id)
        body, content_type = self.storage.open_stream(lead.resume_key)
        return body, content_type, lead.resume_filename
