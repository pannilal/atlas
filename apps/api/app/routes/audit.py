from fastapi import APIRouter
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(limit: int = 100) -> list[dict[str, object]]:
    with SessionLocal() as db:
        rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 500)))).all()
        return [{"id": row.id, "action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id, "details": row.details, "created_at": row.created_at.isoformat()} for row in rows]
