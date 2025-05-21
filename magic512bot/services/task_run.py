from datetime import date, datetime

from sqlalchemy.orm import Session

from magic512bot.config import TIMEZONE
from magic512bot.models.task_run import TaskRun


def set_nomination(session: Session) -> None:
    """Set the last nomination open date to today."""
    task_run = session.query(TaskRun).filter_by(task_name="nominations_open").first()

    if task_run:
        task_run.last_run_date = datetime.now(TIMEZONE).date()
    else:
        task_run = TaskRun(
            task_name="nominations_open",
            last_run_date=datetime.now(TIMEZONE).date(),
        )
        session.add(task_run)


def get_last_nomination_open_date(session: Session) -> date | None:
    """Get the last date nominations were opened."""
    task_run = session.query(TaskRun).filter_by(task_name="nominations_open").first()
    return task_run.last_run_date if task_run else None


def set_poll(session: Session, poll_id: int) -> None:
    """Set the last poll creation date to today and store the poll ID."""
    task_run = session.query(TaskRun).filter_by(task_name="poll_creation").first()

    if task_run:
        task_run.last_run_date = datetime.now(TIMEZONE).date()
        task_run.poll_id = poll_id
    else:
        task_run = TaskRun(
            task_name="poll_creation",
            last_run_date=datetime.now(TIMEZONE).date(),
            poll_id=poll_id,
        )
        session.add(task_run)


def get_active_poll_id(session: Session) -> int | None:
    """Get the ID of the active poll."""
    task_run = session.query(TaskRun).filter_by(task_name="poll_creation").first()
    return task_run.poll_id if task_run else None


def get_poll_last_run_date(session: Session) -> date | None:
    """Get the last date a poll was created."""
    task_run = session.query(TaskRun).filter_by(task_name="poll_creation").first()
    return task_run.last_run_date if task_run else None


def should_run_nominations_this_week(session: Session) -> bool:
    """
    Determine if nominations should run this week.
    Nominations run every other week, starting from the first week of the year.
    """
    today = datetime.now(TIMEZONE).date()
    # Get the week number (1-53)
    week_number = today.isocalendar()[1]
    # Even weeks (0, 2, 4...) will run nominations
    return week_number % 2 == 0
