"""First-boot seed: the single demo attorney + the object-storage bucket (§9.1).

Idempotent - safe to run on every boot.
"""
from __future__ import annotations

import logging

from app.adapters.storage import get_storage
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.repositories.users_repo import UsersRepository

logger = logging.getLogger(__name__)


def seed_attorney() -> None:
    db = SessionLocal()
    try:
        repo = UsersRepository(db)
        if repo.get_by_email(settings.seed_attorney_email) is not None:
            logger.info("Seed attorney already exists; skipping.")
            return
        repo.create(
            email=settings.seed_attorney_email,
            hashed_password=hash_password(settings.seed_attorney_password),
            full_name=settings.seed_attorney_name,
            role="attorney",
        )
        db.commit()
        logger.info(
            "Seeded demo attorney",
            extra={"extra": {"email": settings.seed_attorney_email}},
        )
    finally:
        db.close()


def seed_bucket() -> None:
    get_storage().ensure_bucket()
    logger.info("Ensured object-storage bucket", extra={"extra": {"bucket": settings.s3_bucket}})


def main() -> None:
    configure_logging(settings.log_level)
    seed_bucket()
    seed_attorney()


if __name__ == "__main__":
    main()
