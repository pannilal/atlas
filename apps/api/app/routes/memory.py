from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, Memory
from app.memory_preferences import MemoryPreferences, get_memory_preferences, save_memory_preferences
from app.memory_service import search_memories

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    category: Literal["semantic", "episodic"] = "semantic"


@router.get("")
def search_memory(q: str = "", category: str | None = None, limit: int = 50) -> list[dict[str, object]]:
    with SessionLocal() as db:
        rows = search_memories(db, q, category, limit)
        return [{"id": m.id, "content": m.content, "category": m.category, "created_at": m.created_at.isoformat(), "updated_at": m.updated_at.isoformat()} for m in rows]


@router.get("/settings")
def memory_settings() -> dict[str, bool]:
    return get_memory_preferences().model_dump()


@router.put("/settings")
def update_memory_settings(payload: MemoryPreferences) -> dict[str, bool]:
    save_memory_preferences(payload)
    with SessionLocal() as db:
        db.add(AuditLog(action="memory.preferences_updated", entity_type="settings", entity_id="local", details=payload.model_dump()))
        db.commit()
    return payload.model_dump()


@router.post("")
def create_memory(payload: MemoryCreate) -> dict[str, object]:
    with SessionLocal() as db:
        memory = Memory(content=payload.content.strip(), category=payload.category)
        db.add(memory)
        db.flush()
        db.add(AuditLog(action="memory.created", entity_type="memory", entity_id=memory.id, details={"category": memory.category}))
        db.commit()
        db.refresh(memory)
        return {"id": memory.id, "content": memory.content, "category": memory.category, "created_at": memory.created_at.isoformat()}


@router.delete("/{memory_id}")
def delete_memory(memory_id: str) -> dict[str, str]:
    with SessionLocal() as db:
        memory = db.get(Memory, memory_id)
        if memory is None:
            raise HTTPException(status_code=404, detail="Memory not found.")
        db.add(AuditLog(action="memory.deleted", entity_type="memory", entity_id=memory_id, details={"category": memory.category}))
        db.delete(memory)
        db.commit()
        return {"status": "deleted"}
