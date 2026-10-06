from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from croniter import croniter

from app.database import SessionLocal
from app.models import AuditLog, ScheduledJob

router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    instruction: str = Field(min_length=1, max_length=20000)
    interval_seconds: int | None = Field(default=None, ge=60, le=31 * 24 * 60 * 60)
    cron_expression: str | None = Field(default=None, min_length=9, max_length=100)
    timezone: str = Field(default="UTC", min_length=1, max_length=100)

    @field_validator("name", "instruction")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be blank.")
        return value.strip()

    @field_validator("cron_expression")
    @classmethod
    def valid_cron(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if len(value.split()) != 5 or not croniter.is_valid(value):
            raise ValueError("Use a valid five-field cron expression (minute hour day month weekday).")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value.strip())
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Use a valid IANA timezone, such as Asia/Kolkata or America/New_York.") from exc
        return value.strip()

    @field_validator("cron_expression")
    @classmethod
    def exactly_one_schedule_type(cls, value: str | None, info):
        interval_seconds = info.data.get("interval_seconds")
        if (value is None) == (interval_seconds is None):
            raise ValueError("Choose either an interval or a cron expression.")
        return value


class ScheduleEnable(BaseModel):
    enabled: bool


def _serialize(job: ScheduledJob) -> dict[str, object]:
    interval = int(job.schedule.split(":", 1)[1]) if job.schedule.startswith("every:") else None
    cron_expression = job.schedule[5:] if job.schedule.startswith("cron:") else None
    next_run = job.next_run_at
    if next_run and next_run.tzinfo is None:
        next_run = next_run.replace(tzinfo=timezone.utc)
    return {"id": job.id, "name": job.name, "instruction": job.instruction, "interval_seconds": interval, "cron_expression": cron_expression, "timezone": job.timezone or "UTC", "enabled": job.enabled, "next_run_at": next_run.isoformat() if next_run else None, "created_at": job.created_at.isoformat()}


@router.get("")
def list_schedules() -> list[dict[str, object]]:
    with SessionLocal() as db:
        jobs = db.scalars(select(ScheduledJob).order_by(ScheduledJob.created_at.desc()).limit(200)).all()
        return [_serialize(job) for job in jobs]


@router.post("", status_code=201)
def create_schedule(payload: ScheduleCreate) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    if payload.interval_seconds is None and payload.cron_expression is None:
        raise HTTPException(status_code=422, detail="Provide an interval or a cron expression.")
    schedule = f"every:{payload.interval_seconds}" if payload.interval_seconds is not None else f"cron:{payload.cron_expression}"
    local_now = now.astimezone(ZoneInfo(payload.timezone))
    next_run = timedelta(seconds=payload.interval_seconds) + now if payload.interval_seconds is not None else croniter(payload.cron_expression, local_now).get_next(datetime).astimezone(timezone.utc)
    with SessionLocal() as db:
        job = ScheduledJob(name=payload.name.strip(), instruction=payload.instruction.strip(), schedule=schedule, timezone=payload.timezone, enabled=True, next_run_at=next_run)
        db.add(job)
        db.flush()
        db.add(AuditLog(action="scheduled_job.created", entity_type="scheduled_job", entity_id=job.id, details={"interval_seconds": payload.interval_seconds, "cron_expression": payload.cron_expression, "timezone": payload.timezone}))
        db.commit()
        db.refresh(job)
        return _serialize(job)


@router.put("/{job_id}")
def set_schedule_enabled(job_id: str, payload: ScheduleEnable) -> dict[str, object]:
    with SessionLocal() as db:
        job = db.get(ScheduledJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Scheduled job not found.")
        job.enabled = payload.enabled
        if payload.enabled:
            if job.schedule.startswith("every:"):
                job.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=int(job.schedule.split(":", 1)[1]))
            elif job.schedule.startswith("cron:"):
                local_now = datetime.now(timezone.utc).astimezone(ZoneInfo(job.timezone or "UTC"))
                job.next_run_at = croniter(job.schedule[5:], local_now).get_next(datetime).astimezone(timezone.utc)
        db.add(AuditLog(action="scheduled_job.enabled" if payload.enabled else "scheduled_job.paused", entity_type="scheduled_job", entity_id=job.id, details={}))
        db.commit()
        db.refresh(job)
        return _serialize(job)


@router.delete("/{job_id}", status_code=204)
def delete_schedule(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(ScheduledJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Scheduled job not found.")
        db.add(AuditLog(action="scheduled_job.deleted", entity_type="scheduled_job", entity_id=job.id, details={"name": job.name}))
        db.delete(job)
        db.commit()
