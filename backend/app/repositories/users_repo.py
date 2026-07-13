from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UsersRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def create(self, *, email: str, hashed_password: str, full_name: str, role: str = "attorney") -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name, role=role)
        self.db.add(user)
        self.db.flush()
        return user

    def first_attorney(self) -> User | None:
        return self.db.execute(
            select(User).where(User.role == "attorney").order_by(User.created_at.asc())
        ).scalars().first()
