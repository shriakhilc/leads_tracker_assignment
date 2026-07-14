from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter()


@router.get("/healthz")
def healthz(db: Session = Depends(get_db)) -> dict:
    """Liveness + readiness: also confirms the DB is reachable."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
