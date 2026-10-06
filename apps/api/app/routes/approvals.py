from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database import SessionLocal
from app.models import ApprovalRequest, AuditLog, Task, TaskEvent
from app.workflows.task_graph import schedule_task

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
def list_approvals() -> list[dict[str, object]]:
    with SessionLocal() as db:
        rows = db.scalars(select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc()).limit(100)).all()
        return [{"id": a.id, "task_id": a.task_id, "action": a.action, "description": a.description, "status": a.status, "created_at": a.created_at.isoformat()} for a in rows]


def _resolve(approval_id: str, decision: str) -> dict[str, str]:
    with SessionLocal() as db:
        approval = db.get(ApprovalRequest, approval_id)
        if approval is None:
            raise HTTPException(status_code=404, detail="Approval request not found.")
        if approval.status != "PENDING":
            raise HTTPException(status_code=409, detail="This approval has already been resolved.")
        task = db.get(Task, approval.task_id)
        if task is None or task.status != "WAITING_APPROVAL":
            raise HTTPException(status_code=409, detail="The task is no longer waiting for this approval.")
        approval.status = decision
        approval.resolved_at = datetime.now(timezone.utc)
        db.add(TaskEvent(task_id=approval.task_id, event_type=f"approval_{decision.lower()}", message=f"User {decision.lower()} the requested action."))
        db.add(AuditLog(action=f"approval.{decision.lower()}", entity_type="approval", entity_id=approval.id, details={"task_id": approval.task_id, "action": approval.action}))
        db.commit()
        result = {"id": approval.id, "status": approval.status, "task_id": approval.task_id}
    schedule_task(result["task_id"])
    return {"id": result["id"], "status": result["status"]}


@router.post("/{approval_id}/approve")
async def approve(approval_id: str) -> dict[str, str]:
    return _resolve(approval_id, "APPROVED")


@router.post("/{approval_id}/reject")
async def reject(approval_id: str) -> dict[str, str]:
    return _resolve(approval_id, "REJECTED")
