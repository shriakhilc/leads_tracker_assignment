from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.lead import LeadState


class AssigneeOut(BaseModel):
    attorney_id: uuid.UUID
    email: EmailStr
    full_name: str

    class Config:
        from_attributes = True


class LeadOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    resume_filename: str
    resume_content_type: str
    state: LeadState
    created_at: datetime
    updated_at: datetime
    assignee: AssigneeOut | None = None

    class Config:
        from_attributes = True


class LeadListOut(BaseModel):
    items: list[LeadOut]
    total: int
    limit: int
    offset: int


class LeadStateUpdate(BaseModel):
    state: LeadState = Field(..., description="Target state; only REACHED_OUT is accepted today.")


class ResumeUrlOut(BaseModel):
    url: str
    expires_in: int
