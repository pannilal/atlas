from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_database() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("sqlite"):
        with engine.begin() as connection:
            task_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(tasks)")}
            if "browser_control" not in task_columns:
                connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN browser_control VARCHAR(24) NOT NULL DEFAULT 'agent'")
            columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scheduled_jobs)")}
            if "timezone" not in columns:
                connection.exec_driver_sql("ALTER TABLE scheduled_jobs ADD COLUMN timezone VARCHAR(100) NOT NULL DEFAULT 'UTC'")
