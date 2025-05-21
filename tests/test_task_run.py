from datetime import datetime

from freezegun import freeze_time
from sqlalchemy.orm import Session

from magic512bot.config import TIMEZONE
from magic512bot.models.task_run import TaskRun
from magic512bot.services.task_run import (
    get_active_poll_id,
    get_last_nomination_open_date,
    get_poll_last_run_date,
    set_nomination,
    set_poll,
    should_run_nominations_this_week,
)


def test_get_last_nomination_open_date_no_entry(db_session: Session) -> None:
    """Test getting last nomination open date when no entry exists."""
    result = get_last_nomination_open_date(db_session)
    assert result is None


def test_set_and_get_nomination_date(db_session: Session) -> None:
    """Test setting and getting the nomination date."""
    # Set the nomination date
    set_nomination(db_session)
    db_session.commit()

    # Get the nomination date
    last_date = get_last_nomination_open_date(db_session)
    assert last_date == datetime.now(TIMEZONE).date()

    # Verify the entry was created in the database
    task_run = db_session.query(TaskRun).filter_by(task_name="nominations_open").first()
    assert task_run is not None
    assert task_run.last_run_date == datetime.now(TIMEZONE).date()


def test_get_poll_last_run_date_no_entry(db_session: Session) -> None:
    """Test getting poll last run date when no entry exists."""
    result = get_poll_last_run_date(db_session)
    assert result is None


def test_set_and_get_poll_date_and_id(db_session: Session) -> None:
    """Test setting and getting the poll date and ID."""
    # Set the poll date and ID
    set_poll(db_session, poll_id=12345)
    db_session.commit()

    # Get the poll date and ID
    last_date = get_poll_last_run_date(db_session)
    poll_id = get_active_poll_id(db_session)
    assert last_date == datetime.now(TIMEZONE).date()
    assert poll_id == 12345

    # Verify the entry was created in the database
    task_run = db_session.query(TaskRun).filter_by(task_name="poll_creation").first()
    assert task_run is not None
    assert task_run.last_run_date == datetime.now(TIMEZONE).date()
    assert task_run.poll_id == 12345


def test_update_poll_id(db_session: Session) -> None:
    """Test updating the poll ID."""
    # Set initial poll
    set_poll(db_session, poll_id=12345)
    db_session.commit()

    # Update poll ID
    set_poll(db_session, poll_id=67890)
    db_session.commit()

    # Verify update
    poll_id = get_active_poll_id(db_session)
    assert poll_id == 67890

    # Verify the entry was updated in the database
    task_run = db_session.query(TaskRun).filter_by(task_name="poll_creation").first()
    assert task_run is not None
    assert task_run.poll_id == 67890


def test_should_run_nominations_this_week(db_session: Session) -> None:
    """Test the bi-weekly nomination schedule."""
    # Test even week
    with freeze_time("2024-01-08 12:00:00", tz_offset=0):  # Week 2
        assert should_run_nominations_this_week(db_session) is True

    # Test odd week
    with freeze_time("2024-01-15 12:00:00", tz_offset=0):  # Week 3
        assert should_run_nominations_this_week(db_session) is False

    # Test another even week
    with freeze_time("2024-01-22 12:00:00", tz_offset=0):  # Week 4
        assert should_run_nominations_this_week(db_session) is True

    # Test another odd week
    with freeze_time("2024-01-29 12:00:00", tz_offset=0):  # Week 5
        assert should_run_nominations_this_week(db_session) is False
