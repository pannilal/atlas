from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, Task, TaskEvent, TaskStep, ToolExecution
from app.workflows.task_graph import cancel_task, schedule_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    instruction: str = Field(min_length=1, max_length=20000)
    conversation_id: str | None = None


def _task_data(db, task: Task) -> dict[str, object]:
    steps = db.scalars(select(TaskStep).where(TaskStep.task_id == task.id).order_by(TaskStep.position)).all()
    events = db.scalars(select(TaskEvent).where(TaskEvent.task_id == task.id).order_by(TaskEvent.created_at)).all()
    tools = db.scalars(select(ToolExecution).where(ToolExecution.task_id == task.id).order_by(ToolExecution.created_at)).all()
    return {
        "id": task.id, "instruction": task.instruction, "status": task.status,
        "result": task.result, "error": task.error, "browser_control": task.browser_control,
        "created_at": task.created_at.isoformat(),
        "steps": [{"id": s.id, "position": s.position, "name": s.name, "status": s.status, "detail": s.detail} for s in steps],
        "events": [{"id": e.id, "event_type": e.event_type, "message": e.message, "created_at": e.created_at.isoformat()} for e in events],
        "tool_executions": [{"id": tool.id, "tool_name": tool.tool_name, "arguments": tool.arguments, "status": tool.status, "result": tool.result, "error": tool.error, "created_at": tool.created_at.isoformat(), "completed_at": tool.completed_at.isoformat() if tool.completed_at else None} for tool in tools],
    }


@router.get("")
def list_tasks(limit: int = 50) -> list[dict[str, object]]:
    with SessionLocal() as db:
        rows = db.scalars(select(Task).order_by(Task.created_at.desc()).limit(max(1, min(limit, 100)))).all()
        ids = [task.id for task in rows]
        tool_rows = db.scalars(select(ToolExecution).where(ToolExecution.task_id.in_(ids)).order_by(ToolExecution.created_at)).all() if ids else []
        tools_by_task: dict[str, list[ToolExecution]] = {}
        for tool in tool_rows:
            tools_by_task.setdefault(tool.task_id, []).append(tool)
        return [{"id": task.id, "instruction": task.instruction, "status": task.status, "browser_control": task.browser_control, "created_at": task.created_at.isoformat(), "result": task.result, "error": task.error, "tool_executions": [{"id": tool.id, "tool_name": tool.tool_name, "status": tool.status, "created_at": tool.created_at.isoformat(), "completed_at": tool.completed_at.isoformat() if tool.completed_at else None} for tool in tools_by_task.get(task.id, [])]} for task in rows]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_task(payload: TaskCreate) -> dict[str, object]:
    with SessionLocal() as db:
        task = Task(instruction=payload.instruction.strip(), conversation_id=payload.conversation_id, status="PENDING")
        db.add(task)
        db.flush()
        db.add(TaskEvent(task_id=task.id, event_type="created", message="Task queued."))
        db.add(AuditLog(action="task.created", entity_type="task", entity_id=task.id, details={}))
        db.commit()
        task_id = task.id
    schedule_task(task_id)
    return {"id": task_id, "status": "PENDING", "instruction": payload.instruction.strip()}


@router.get("/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        return _task_data(db, task)


@router.post("/{task_id}/cancel")
def stop_task(task_id: str) -> dict[str, str]:
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        if task.status in {"COMPLETED", "FAILED", "CANCELLED"}:
            raise HTTPException(status_code=409, detail=f"Task is already {task.status.lower()}.")
        task.status = "CANCELLED"
        task.completed_at = datetime.now(timezone.utc)
        db.add(TaskEvent(task_id=task.id, event_type="cancelled", message="Task cancelled by the user."))
        db.add(AuditLog(action="task.cancelled", entity_type="task", entity_id=task.id, details={}))
        db.commit()
    cancel_task(task_id)
    return {"id": task_id, "status": "CANCELLED"}


@router.post("/{task_id}/browser-control/{action}")
async def control_browser(task_id: str, action: str) -> dict[str, str]:
    if action not in {"takeover", "resume"}:
        raise HTTPException(status_code=404, detail="Unknown browser control action.")
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        browser_tool = db.scalars(select(ToolExecution).where(ToolExecution.task_id == task_id, ToolExecution.tool_name == "browser_task", ToolExecution.status == "RUNNING").limit(1)).first()
        if browser_tool is None:
            raise HTTPException(status_code=409, detail="This task has no active browser operation.")
        try:
            from app.agents.browser import browser_control
            await browser_control(task_id, action)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        task.browser_control = "user" if action == "takeover" else "agent"
        task.status = "WAITING_USER" if action == "takeover" else "RUNNING"
        db.add(TaskEvent(task_id=task_id, event_type=f"browser_{action}", message="User took over the browser." if action == "takeover" else "User returned browser control to Atlas."))
        db.add(AuditLog(action=f"browser.{action}", entity_type="task", entity_id=task_id, details={}))
        db.commit()
    return {"id": task_id, "browser_control": "user" if action == "takeover" else "agent"}
