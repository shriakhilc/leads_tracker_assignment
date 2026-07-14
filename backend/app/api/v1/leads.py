from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import LeadState, User
from app.schemas.lead import LeadListOut, LeadOut, LeadStateUpdate, ResumeUrlOut
from app.services.assignment.base import AssignmentError
from app.services.email_service import send_submission_emails
from app.services.exceptions import (
    IllegalStateTransition,
    NotFoundError,
    UploadTooLarge,
    UploadValidationError,
)
from app.services.leads_service import LeadsService

router = APIRouter()

_email_adapter = TypeAdapter(EmailStr)


# --- F1–F3: public submission ---
@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
async def submit_lead(
    background_tasks: BackgroundTasks,
    first_name: str = Form(..., min_length=1, max_length=200),
    last_name: str = Form(..., min_length=1, max_length=200),
    email: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> LeadOut:
    """Public, unauthenticated lead submission (multipart)."""
    try:
        validated_email = _email_adapter.validate_python(email)
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address")

    # Read within the size cap so an oversized upload can't exhaust memory.
    resume_bytes = await resume.read(settings.max_upload_bytes + 1)
    if len(resume_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Resume exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit.",
        )

    service = LeadsService(db)
    try:
        lead = service.submit_lead(
            first_name=first_name,
            last_name=last_name,
            email=str(validated_email),
            resume_bytes=resume_bytes,
            resume_filename=resume.filename or "resume",
            resume_content_type=resume.content_type or "application/octet-stream",
        )
    except UploadTooLarge as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))
    except UploadValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssignmentError:
        # Persistence rolled back → nobody is notified (§3, step 4).
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not assign the lead. Please try again later.",
        )

    # Post-commit side effect only: emails scheduled after a successful commit (N4).
    background_tasks.add_task(send_submission_emails, lead.id)
    return service.to_out(lead)


# --- F4: list ---
@router.get("", response_model=LeadListOut)
def list_leads(
    state: LeadState | None = Query(default=None),
    assigned_to_me: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="created_at", pattern="^(created_at|state|email|name|assignee)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeadListOut:
    # "assigned to me" is derived from the token, never a client value (§5).
    assigned_to = current_user.id if assigned_to_me else None
    items, total = LeadsService(db).list_leads(
        state=state, assigned_to=assigned_to, limit=limit, offset=offset, sort=sort, order=order
    )
    return LeadListOut(items=items, total=total, limit=limit, offset=offset)


# --- F6: get one ---
@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeadOut:
    service = LeadsService(db)
    try:
        lead = service.get_lead(lead_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return service.to_out(lead)


# --- F6: resume download ---
@router.get("/{lead_id}/resume")
def get_resume(
    lead_id: uuid.UUID,
    presigned: bool = Query(default=False, description="Return a short-lived URL instead of a stream."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeadsService(db)
    try:
        if presigned:
            url, ttl = service.resume_presigned_url(lead_id)
            return ResumeUrlOut(url=url, expires_in=ttl)
        body, content_type, filename = service.resume_stream(lead_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    return StreamingResponse(
        body,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- F5: state transition ---
@router.patch("/{lead_id}/state", response_model=LeadOut)
def update_state(
    lead_id: uuid.UUID,
    body: LeadStateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeadOut:
    service = LeadsService(db)
    try:
        lead = service.transition_state(lead_id, body.state)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    except IllegalStateTransition as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return service.to_out(lead)
