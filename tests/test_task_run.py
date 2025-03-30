from datetime import date, datetime

import pytest
from sqlalchemy.orm import Session

from magic512bot.services.task_run import (
    get_active_poll_id,
    get_last_nomination_open_date,
    get_poll_last_run_date,
    set_nomination,
    set_poll,
)


def test_get_last_nomination_open_date_no_entry(db_session: Session) -> None:
    """Test getting last nomination open date when no entry exists."""
    result = get_last_nomination_open_date(db_session)
    assert result is None


def test_set_and_get_nomination_date(db_session: Session) -> None:
    """Test setting and getting nomination open date."""
    set_nomination(db_session)
    result = get_last_nomination_open_date(db_session)
    assert result == datetime.now().date()


def test_get_poll_last_run_date_no_entry(db_session: Session) -> None:
    """Test getting poll last run date when no entry exists."""
    result = get_poll_last_run_date(db_session)
    assert result is None


def test_set_and_get_poll_date_and_id(db_session: Session) -> None:
    """Test setting and getting poll date and ID."""
    test_id = 12345
    set_poll(db_session, test_id)

    date_result = get_poll_last_run_date(db_session)
    id_result = get_active_poll_id(db_session)

    assert date_result == datetime.now().date()
    assert id_result == test_id


def test_update_poll_id(db_session: Session) -> None:
    """Test updating an existing poll ID."""
    initial_id = 12345
    new_id = 67890

    set_poll(db_session, initial_id)
    set_poll(db_session, new_id)

    result = get_active_poll_id(db_session)
    assert result == new_id
