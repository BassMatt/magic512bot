import datetime
from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from magic512bot.services.task_run import (
    get_active_poll_id,
    get_last_run_date,
    set_active_poll_id,
    set_last_run_date,
)


def test_get_last_run_date_no_entry(db_session: Session) -> None:
    """Test getting last run date when no entry exists."""
    result = get_last_run_date(db_session, "test_task")
    assert result is None


def test_set_and_get_last_run_date(db_session: Session) -> None:
    """Test setting and getting last run date."""
    test_date = datetime.date.today()
    set_last_run_date(db_session, "test_task", test_date)

    result = get_last_run_date(db_session, "test_task")
    assert result == test_date


def test_update_last_run_date(db_session: Session) -> None:
    """Test updating an existing last run date."""
    initial_date = datetime.date.today()
    set_last_run_date(db_session, "test_task", initial_date)

    new_date = initial_date + datetime.timedelta(days=1)
    set_last_run_date(db_session, "test_task", new_date)

    result = get_last_run_date(db_session, "test_task")
    assert result == new_date


def test_get_active_poll_id_no_entry(db_session: Session) -> None:
    """Test getting active poll ID when no entry exists."""
    result = get_active_poll_id(db_session)
    assert result is None


def test_set_and_get_active_poll_id(db_session: Session) -> None:
    """Test setting and getting active poll ID."""
    test_id = 12345
    set_active_poll_id(db_session, test_id)

    result = get_active_poll_id(db_session)
    assert result == test_id


def test_update_active_poll_id(db_session: Session) -> None:
    """Test updating an existing active poll ID."""
    initial_id = 12345
    set_active_poll_id(db_session, initial_id)

    new_id = 67890
    set_active_poll_id(db_session, new_id)

    result = get_active_poll_id(db_session)
    assert result == new_id


def test_clear_active_poll_id(db_session: Session) -> None:
    """Test clearing the active poll ID by setting it to None."""
    initial_id = 12345
    set_active_poll_id(db_session, initial_id)

    set_active_poll_id(db_session, None)

    result = get_active_poll_id(db_session)
    assert result is None
