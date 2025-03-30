from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from magic512bot.config import TIMEZONE
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


NOMINATION_PERIOD_SCENARIOS = [
    pytest.param(
        "2024-03-14 14:00:00", True, id="thursday_9am_open"
    ),  # 9 AM EST = 14:00 UTC
    pytest.param("2024-03-14 13:59:00", False, id="thursday_before_9am_closed"),
    pytest.param("2024-03-17 13:59:00", True, id="sunday_before_9am_open"),
    pytest.param("2024-03-17 14:00:00", False, id="sunday_9am_closed"),
]

patch(
    "magic512bot.services.task_run.get_last_nomination_open_date",
    return_value=datetime.now(TIMEZONE).date() - timedelta(days=1),
)
