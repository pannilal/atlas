from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications() -> list[dict[str, object]]:
    with SessionLocal() as db:
        rows = db.scalars(select(Notification).order_by(Notification.created_at.desc()).limit(100)).all()
        return [{"id": n.id, "title": n.title, "message": n.message, "category": n.category, "read": n.read, "created_at": n.created_at.isoformat()} for n in rows]


@router.post("/{notification_id}/read")
def mark_read(notification_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        notification = db.get(Notification, notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found.")
        notification.read = True
        db.commit()
        return {"id": notification.id, "read": True}
