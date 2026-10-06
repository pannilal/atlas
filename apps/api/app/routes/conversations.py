from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models import Conversation, Message, utcnow

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
def list_conversations() -> list[dict[str, object]]:
    with SessionLocal() as db:
        rows = db.scalars(select(Conversation).order_by(Conversation.updated_at.desc()).limit(100)).all()
        return [{"id": row.id, "title": row.title, "updated_at": row.updated_at.isoformat()} for row in rows]


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        row = db.scalar(select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conversation_id))
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        messages = sorted(row.messages, key=lambda message: message.created_at)
        return {"id": row.id, "title": row.title, "messages": [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages]}


@router.post("/{conversation_id}/title")
def rename_conversation(conversation_id: str, payload: dict[str, str]) -> dict[str, str]:
    title = payload.get("title", "").strip()
    if not title or len(title) > 200:
        raise HTTPException(status_code=422, detail="Title must be between 1 and 200 characters.")
    with SessionLocal() as db:
        row = db.get(Conversation, conversation_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        row.title = title
        row.updated_at = utcnow()
        db.commit()
        return {"id": row.id, "title": row.title}


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str) -> dict[str, str]:
    with SessionLocal() as db:
        row = db.get(Conversation, conversation_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        db.delete(row)
        db.commit()
        return {"status": "deleted"}
