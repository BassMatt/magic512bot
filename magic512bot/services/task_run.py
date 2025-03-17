from datetime import date

from sqlalchemy.orm import Session

from magic512bot.models.task_run import TaskRun


def get_last_run_date(session: Session, task_name: str) -> date | None:
    """Get the last run date for a task."""
    task_run = session.query(TaskRun).filter(TaskRun.task_name == task_name).first()
    return task_run.last_run_date if task_run else None


def set_last_run_date(session: Session, task_name: str, run_date: date) -> None:
    """Set the last run date for a task."""
    task_run = session.query(TaskRun).filter(TaskRun.task_name == task_name).first()
    if task_run:
        task_run.last_run_date = run_date
    else:
        task_run = TaskRun(task_name=task_name, last_run_date=run_date)
        session.add(task_run)


def get_active_poll_id(session: Session) -> int | None:
    """Get the active poll ID."""
    task_run = (
        session.query(TaskRun).filter(TaskRun.task_name == "poll_tracking").first()
    )
    return task_run.active_poll_id if task_run else None


def set_active_poll_id(session: Session, poll_id: int | None) -> None:
    """Set the active poll ID."""
    task_run = (
        session.query(TaskRun).filter(TaskRun.task_name == "poll_tracking").first()
    )
    if task_run:
        task_run.active_poll_id = poll_id
    else:
        task_run = TaskRun(
            task_name="poll_tracking",
            last_run_date=date.today(),
            active_poll_id=poll_id,
        )
        session.add(task_run)
