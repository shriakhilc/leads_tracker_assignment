"""Unit tests for the leads service: filename hygiene, upload validation,
the state machine, and submission orchestration/transaction ordering.

The DB session, repositories, assignment strategy, and object storage are all
mocked, so these exercise the service logic in isolation.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.models import LeadState
from app.services import leads_service
from app.services.leads_service import LeadsService, _sanitize_filename
from app.services.exceptions import (
    IllegalStateTransition,
    NotFoundError,
    UploadTooLarge,
    UploadValidationError,
)

from tests.conftest import make_lead


@pytest.fixture
def service(mock_db, monkeypatch):
    """A LeadsService with storage and repositories replaced by mocks."""
    monkeypatch.setattr(leads_service, "get_storage", lambda: MagicMock(name="storage"))
    svc = LeadsService(mock_db)
    svc.leads = MagicMock(name="LeadsRepository")
    svc.assignments = MagicMock(name="AssignmentsRepository")
    svc.strategy = MagicMock(name="AssignmentStrategy")
    return svc


# --- _sanitize_filename ---------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("resume.pdf", "resume.pdf"),
        ("../../../etc/passwd", "passwd"),               # path traversal stripped
        ("C:\\Users\\ada\\resume.docx", "resume.docx"),  # windows path stripped
        ("my resume (final).pdf", "my_resume_final_.pdf"),  # unsafe chars -> _
        ("", "resume"),                                   # empty -> fallback
        ("@@@", "resume"),                                # all-unsafe -> fallback
        ("....", "resume"),                               # dots-only -> fallback
    ],
)
def test_sanitize_filename(raw, expected):
    assert _sanitize_filename(raw) == expected


def test_sanitize_filename_handles_none():
    assert _sanitize_filename(None) == "resume"


def test_sanitize_filename_truncates_long_names():
    out = _sanitize_filename("a" * 300 + ".pdf")
    assert len(out) == 200


# --- _validate_upload -----------------------------------------------------

def test_validate_upload_accepts_valid_pdf(service):
    # Should not raise.
    service._validate_upload("application/pdf", size=1024)


def test_validate_upload_rejects_empty_file(service):
    with pytest.raises(UploadValidationError):
        service._validate_upload("application/pdf", size=0)


def test_validate_upload_rejects_oversized_file(service):
    from app.core.config import settings

    with pytest.raises(UploadTooLarge):
        service._validate_upload("application/pdf", size=settings.max_upload_bytes + 1)


def test_validate_upload_rejects_unsupported_type(service):
    with pytest.raises(UploadValidationError):
        service._validate_upload("image/png", size=1024)


# --- transition_state (state machine) -------------------------------------

def test_transition_pending_to_reached_out(service):
    lead = make_lead(state=LeadState.PENDING)
    service.leads.get.return_value = lead

    result = service.transition_state(lead.id, LeadState.REACHED_OUT)

    assert result.state == LeadState.REACHED_OUT
    service.db.commit.assert_called_once()


def test_transition_reached_out_back_to_pending_is_allowed(service):
    lead = make_lead(state=LeadState.REACHED_OUT)
    service.leads.get.return_value = lead

    result = service.transition_state(lead.id, LeadState.PENDING)

    assert result.state == LeadState.PENDING
    service.db.commit.assert_called_once()


def test_transition_to_same_state_is_idempotent_noop(service):
    lead = make_lead(state=LeadState.PENDING)
    service.leads.get.return_value = lead

    result = service.transition_state(lead.id, LeadState.PENDING)

    assert result.state == LeadState.PENDING
    service.db.commit.assert_not_called()


def test_illegal_transition_raises_and_does_not_commit(service, monkeypatch):
    # Remove PENDING's allowed targets so the guard rejects the transition.
    monkeypatch.setattr(leads_service, "_ALLOWED_TRANSITIONS", {LeadState.PENDING: set()})
    lead = make_lead(state=LeadState.PENDING)
    service.leads.get.return_value = lead

    with pytest.raises(IllegalStateTransition):
        service.transition_state(lead.id, LeadState.REACHED_OUT)
    service.db.commit.assert_not_called()


def test_transition_missing_lead_raises_not_found(service):
    service.leads.get.return_value = None
    with pytest.raises(NotFoundError):
        service.transition_state(uuid.uuid4(), LeadState.REACHED_OUT)


def test_get_lead_missing_raises_not_found(service):
    service.leads.get.return_value = None
    with pytest.raises(NotFoundError):
        service.get_lead(uuid.uuid4())


# --- submit_lead (orchestration + transaction boundary) -------------------

def _submit(service):
    return service.submit_lead(
        first_name="  Ada ",
        last_name=" Lovelace ",
        email=" ada@example.com ",
        resume_bytes=b"%PDF-1.4 fake",
        resume_filename="resume.pdf",
        resume_content_type="application/pdf",
    )


def test_submit_lead_happy_path_uploads_persists_and_assigns(service):
    lead = make_lead()
    service.leads.add.return_value = lead
    attorney_id = uuid.uuid4()
    service.strategy.assign.return_value = attorney_id

    result = _submit(service)

    assert result is lead
    # Resume uploaded to storage with the right content type.
    service.storage.put.assert_called_once()
    assert service.storage.put.call_args.args[2] == "application/pdf"
    # Lead + assignment written, then committed exactly once.
    service.assignments.create_active.assert_called_once_with(
        lead_id=lead.id, attorney_id=attorney_id
    )
    service.db.commit.assert_called_once()
    service.db.rollback.assert_not_called()


def test_submit_lead_strips_whitespace_on_persisted_fields(service):
    captured = {}

    def _capture(lead_obj):
        captured["lead"] = lead_obj
        lead_obj.id = uuid.uuid4()
        return lead_obj

    service.leads.add.side_effect = _capture
    service.strategy.assign.return_value = uuid.uuid4()

    _submit(service)

    persisted = captured["lead"]
    assert persisted.first_name == "Ada"
    assert persisted.last_name == "Lovelace"
    assert persisted.email == "ada@example.com"


def test_submit_lead_rolls_back_when_assignment_fails(service):
    service.leads.add.return_value = make_lead()
    service.strategy.assign.side_effect = RuntimeError("no attorney")

    with pytest.raises(RuntimeError):
        _submit(service)

    service.db.rollback.assert_called_once()
    service.db.commit.assert_not_called()


def test_submit_lead_rejects_bad_type_before_touching_storage(service):
    with pytest.raises(UploadValidationError):
        service.submit_lead(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            resume_bytes=b"data",
            resume_filename="x.png",
            resume_content_type="image/png",
        )
    # Validation short-circuits: nothing is uploaded or persisted.
    service.storage.put.assert_not_called()
    service.leads.add.assert_not_called()
