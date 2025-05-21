from datetime import date

from sqlalchemy import BigInteger, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TaskRun(Base):
    """Model to track when tasks were last run and store active poll ID."""

    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_run_date: Mapped[date] = mapped_column(Date, nullable=False)
    poll_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
