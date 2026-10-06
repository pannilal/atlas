import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.health import router as health_router
from app.routes.chat import router as chat_router
from app.routes.settings import router as settings_router
from app.routes.conversations import router as conversations_router
from app.routes.tasks import router as tasks_router
from app.routes.memory import router as memory_router
from app.routes.approvals import router as approvals_router
from app.routes.audit import router as audit_router
from app.routes.notifications import router as notifications_router
from app.routes.security import router as security_router
from app.routes.schedules import router as schedules_router
from app.routes.integrations import router as integrations_router
from app.database import init_database, SessionLocal
from app.models import ApprovalRequest, Task, TaskEvent
from app.workflows.task_graph import schedule_task
from app.workflows.scheduler import scheduler_loop
from sqlalchemy import select


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    with SessionLocal() as db:
        unfinished = db.scalars(select(Task).where(Task.status.in_(["PENDING", "PLANNING", "RUNNING"]))).all()
        recovered_ids = []
        interrupted_browser_tasks = db.scalars(select(Task).where(Task.status == "WAITING_USER")).all()
        for task in interrupted_browser_tasks:
            task.status = "FAILED"
            task.error = "Atlas restarted while browser control was with the user. Start a new task to continue."
            task.completed_at = datetime.now(timezone.utc)
            db.add(TaskEvent(task_id=task.id, event_type="browser_interrupted", message="Browser session ended because Atlas restarted during user takeover."))
        for task in unfinished:
            if task.status != "PENDING":
                task.status = "PENDING"
                db.add(TaskEvent(task_id=task.id, event_type="recovered", message="Task resumed after Atlas restarted."))
            recovered_ids.append(task.id)
        approved_waiting_ids = db.scalars(
            select(Task.id)
            .join(ApprovalRequest, ApprovalRequest.task_id == Task.id)
            .where(Task.status == "WAITING_APPROVAL", ApprovalRequest.status.in_(["APPROVED", "REJECTED"]))
            .distinct()
        ).all()
        for task_id in approved_waiting_ids:
            task = db.get(Task, task_id)
            task.status = "PENDING"
            db.add(TaskEvent(task_id=task_id, event_type="recovered", message="A resolved approval was found after restart; the task is resuming."))
            recovered_ids.append(task_id)
        db.commit()
    for task_id in recovered_ids:
        schedule_task(task_id)
    scheduler_worker = asyncio.create_task(scheduler_loop(), name="atlas-scheduler")
    try:
        yield
    finally:
        scheduler_worker.cancel()
        try:
            await scheduler_worker
        except asyncio.CancelledError:
            pass

app = FastAPI(title="BaysysTech Atlas API", version="0.2.0", docs_url="/docs", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(security_router, prefix="/api/v1")
app.include_router(schedules_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
