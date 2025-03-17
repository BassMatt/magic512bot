from datetime import date

from sqlalchemy import BigInteger, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TaskRun(Base):
    """Model to track when tasks were last run and store active poll ID."""

    __tablename__ = "task_runs"

    task_name: Mapped[str] = mapped_column(String, primary_key=True)
    last_run_date: Mapped[date] = mapped_column(Date, nullable=False)
    active_poll_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
