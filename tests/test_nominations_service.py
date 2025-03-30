from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from magic512bot.models.nomination import Nomination
from magic512bot.services.nomination import (
    add_nomination,
    clear_all_nominations,
    get_all_nominations,
    get_user_nominations,
)


def test_add_nomination_new_user(db_session: Session) -> None:
    """Test adding a nomination for a new user."""
    # Add a nomination
    add_nomination(db_session, user_id=12345, format="Modern")
    db_session.commit()

    # Verify the nomination was added
    nominations = db_session.query(Nomination).all()
    assert len(nominations) == 1
    assert nominations[0].user_id == 12345
    assert nominations[0].format == "Modern"


def test_add_nomination_existing_user(db_session: Session) -> None:
    """Test adding a nomination for an existing user."""
    # Add an initial nomination
    add_nomination(db_session, user_id=12345, format="Modern")
    db_session.commit()

    # Add another nomination for the same user
    add_nomination(db_session, user_id=12345, format="Standard")
    db_session.commit()

    # Verify the nomination was updated
    nominations = db_session.query(Nomination).all()
    assert len(nominations) == 2


def test_add_nomination_multiple_users(db_session: Session) -> None:
    """Test adding nominations for multiple users."""
    # Add nominations for different users
    with db_session.no_autoflush:  # Prevent premature autoflush
        add_nomination(db_session, user_id=12345, format="Modern")
        add_nomination(db_session, user_id=67890, format="Standard")
        db_session.commit()

    # Verify both nominations were added
    nominations = db_session.query(Nomination).all()
    assert len(nominations) == 2

    # Sort by user_id to ensure consistent test results
    nominations.sort(key=lambda n: n.user_id)
    assert nominations[0].user_id == 12345
    assert nominations[0].format == "Modern"
    assert nominations[1].user_id == 67890
    assert nominations[1].format == "Standard"


def test_add_nomination_error_handling(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test error handling when adding a nomination."""

    # Mock the session.execute to raise an exception
    def mock_execute(*args: Any, **kwargs: Any) -> None:
        raise SQLAlchemyError("Database error")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Attempt to add a nomination
    with pytest.raises(SQLAlchemyError):
        add_nomination(db_session, user_id=12345, format="Modern")


def test_get_all_nominations_empty(db_session: Session) -> None:
    """Test getting all nominations when there are none."""
    nominations = get_all_nominations(db_session)
    assert len(nominations) == 0


def test_get_all_nominations(db_session: Session) -> None:
    """Test getting all nominations."""
    # Add some nominations
    with db_session.no_autoflush:  # Prevent premature autoflush
        add_nomination(db_session, user_id=12345, format="Modern")
        add_nomination(db_session, user_id=67890, format="Standard")
        db_session.commit()

    # Get all nominations
    nominations = get_all_nominations(db_session)
    assert len(nominations) == 2

    # Sort by user_id to ensure consistent test results
    nominations.sort(key=lambda n: n.user_id)
    assert nominations[0].user_id == 12345
    assert nominations[0].format == "Modern"
    assert nominations[1].user_id == 67890
    assert nominations[1].format == "Standard"


def test_get_all_nominations_error_handling(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test error handling when getting all nominations."""

    # Mock the session.execute to raise an exception
    def mock_execute(*args: Any, **kwargs: Any) -> None:
        raise SQLAlchemyError("Database error")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Attempt to get all nominations
    nominations = get_all_nominations(db_session)
    assert len(nominations) == 0  # Should return empty list on error


def test_get_user_nominations_empty(db_session: Session) -> None:
    """Test getting nominations for a user that doesn't exist."""
    nominations = get_user_nominations(db_session, user_id=12345)
    assert len(nominations) == 0


def test_get_user_nominations(db_session: Session) -> None:
    """Test getting nominations for a specific user."""
    # Add nominations for different users
    with db_session.no_autoflush:  # Prevent premature autoflush
        add_nomination(db_session, user_id=12345, format="Modern")
        add_nomination(db_session, user_id=67890, format="Standard")
        db_session.commit()

    # Get nominations for one user
    nominations = get_user_nominations(db_session, user_id=12345)
    assert len(nominations) == 1
    assert nominations[0].user_id == 12345
    assert nominations[0].format == "Modern"


def test_get_user_nominations_error_handling(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test error handling when getting user nominations."""

    # Mock the session.execute to raise an exception
    def mock_execute(*args: Any, **kwargs: Any) -> None:
        raise SQLAlchemyError("Database error")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Attempt to get user nominations
    nominations = get_user_nominations(db_session, user_id=12345)
    assert len(nominations) == 0  # Should return empty list on error


def test_clear_all_nominations(db_session: Session) -> None:
    """Test clearing all nominations."""
    # Add some nominations
    with db_session.no_autoflush:  # Prevent premature autoflush
        add_nomination(db_session, user_id=12345, format="Modern")
        add_nomination(db_session, user_id=67890, format="Standard")
        db_session.commit()

    # Verify nominations were added
    assert len(get_all_nominations(db_session)) == 2

    # Clear all nominations
    count = clear_all_nominations(db_session)
    db_session.commit()

    # Verify nominations were cleared
    assert count == 2
    assert len(get_all_nominations(db_session)) == 0


def test_clear_all_nominations_empty(db_session: Session) -> None:
    """Test clearing all nominations when there are none."""
    count = clear_all_nominations(db_session)
    db_session.commit()
    assert count == 0


def test_clear_all_nominations_error_handling(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test error handling when clearing all nominations."""

    # Mock the session.execute to raise an exception
    def mock_execute(*args: Any, **kwargs: Any) -> None:
        raise SQLAlchemyError("Database error")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Attempt to clear all nominations
    count = clear_all_nominations(db_session)
    assert count == 0  # Should return 0 on error


def test_add_nomination_format_too_long(db_session: Session) -> None:
    """Test adding a nomination with a format that's too long."""
    # Create a format that's too long (>55 characters)
    long_format = "A" * 56

    # Attempt to add a nomination with a format that's too long
    with pytest.raises(ValueError) as excinfo:
        add_nomination(db_session, user_id=12345, format=long_format)

    # Verify the error message
    assert "Format is too long" in str(excinfo.value)
