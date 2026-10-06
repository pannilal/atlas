import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from croniter import croniter

from app.database import SessionLocal
from app.models import AuditLog, ScheduledJob, Task, TaskEvent
from app.workflows.task_graph import schedule_task

logger = logging.getLogger(__name__)


def _next_run(job: ScheduledJob, now: datetime) -> datetime:
    value = job.schedule
    if value.startswith("every:"):
        seconds = int(value.split(":", 1)[1])
        if seconds < 60 or seconds > 31 * 24 * 60 * 60:
            raise ValueError("Schedule interval must be between one minute and 31 days")
        return now + timedelta(seconds=seconds)
    if value.startswith("cron:"):
        local_now = now.astimezone(ZoneInfo(job.timezone or "UTC"))
        return croniter(value[5:], local_now).get_next(datetime).astimezone(timezone.utc)
    raise ValueError("Unsupported schedule format")


async def scheduler_loop() -> None:
    while True:
        try:
            now = datetime.now(timezone.utc)
            queued: list[str] = []
            with SessionLocal() as db:
                due = db.scalars(
                    select(ScheduledJob)
                    .where(ScheduledJob.enabled.is_(True), ScheduledJob.next_run_at.is_not(None), ScheduledJob.next_run_at <= now)
                    .order_by(ScheduledJob.next_run_at)
                    .limit(25)
                ).all()
                for job in due:
                    try:
                        next_run = _next_run(job, now)
                    except (ValueError, TypeError, ZoneInfoNotFoundError):
                        job.enabled = False
                        db.add(AuditLog(action="scheduled_job.disabled", entity_type="scheduled_job", entity_id=job.id, details={"reason": "invalid_schedule"}))
                        continue
                    task = Task(instruction=job.instruction, status="PENDING")
                    db.add(task)
                    db.flush()
                    db.add(TaskEvent(task_id=task.id, event_type="scheduled", message=f"Started from scheduled job: {job.name}.", data={"scheduled_job_id": job.id}))
                    db.add(AuditLog(action="scheduled_job.triggered", entity_type="scheduled_job", entity_id=job.id, details={"task_id": task.id}))
                    job.next_run_at = next_run
                    queued.append(task.id)
                db.commit()
            for task_id in queued:
                schedule_task(task_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Atlas recurring-task scheduler iteration failed")
        await asyncio.sleep(10)
