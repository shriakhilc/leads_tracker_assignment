from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models import User
from app.repositories.users_repo import UsersRepository


class AuthService:
    def __init__(self, db: Session):
        self.users = UsersRepository(db)

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            return None
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email, "role": user.role},
        )
