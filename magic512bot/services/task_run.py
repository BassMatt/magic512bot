from datetime import date, datetime

from sqlalchemy.orm import Session

from magic512bot.config import TIMEZONE
from magic512bot.models.task_run import TaskRun


def set_nomination(session: Session) -> None:
    """Set the last run date for a task."""
    task_run = session.query(TaskRun).filter(TaskRun.task_name == "nominations").first()
    run_date = datetime.now(TIMEZONE).date()
    if task_run:
        task_run.last_run_date = run_date
    else:
        task_run = TaskRun(task_name="nominations", last_run_date=run_date)
        session.add(task_run)


def get_last_nomination_open_date(session: Session) -> date | None:
    """Get the last run date for a task."""
    task_run = session.query(TaskRun).filter(TaskRun.task_name == "nominations").first()
    return task_run.last_run_date if task_run else None


def set_poll(session: Session, poll_id: int) -> None:
    """Set the last run date for a task."""
    task_run = session.query(TaskRun).filter(TaskRun.task_name == "poll").first()
    run_date = datetime.now(TIMEZONE).date()
    if task_run:
        task_run.last_run_date = run_date
        task_run.active_poll_id = poll_id
    else:
        task_run = TaskRun(
            task_name="poll",
            last_run_date=run_date,
            active_poll_id=poll_id,
        )
        session.add(task_run)


def get_active_poll_id(session: Session) -> int | None:
    """Get the active poll ID."""
    task_run = session.query(TaskRun).filter(TaskRun.task_name == "poll").first()
    return task_run.active_poll_id if task_run else None


def get_poll_last_run_date(session: Session) -> date | None:
    """Get the last run date for a task."""
    task_run = session.query(TaskRun).filter(TaskRun.task_name == "poll").first()
    return task_run.last_run_date if task_run else None
