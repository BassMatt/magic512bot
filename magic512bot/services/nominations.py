from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from magic512bot.config import LOGGER
from magic512bot.models.nominations import Nominations


def add_nomination(session: Session, user_id: int, format: str) -> None:
    """Add a format nomination to the database."""
    try:
        if len(format) > 55:
            raise ValueError("Format is too long")
        # Check if user already has a nomination
        existing = session.execute(
            select(Nominations).where(Nominations.user_id == user_id)
        ).scalar_one_or_none()

        if existing:
            # Update existing nomination
            existing.format = format
        else:
            # Create new nomination
            nomination = Nominations(user_id=user_id, format=format)
            session.add(nomination)

    except Exception as e:
        LOGGER.error(f"Error adding nomination for user {user_id}: {e!s}")
        raise


def get_all_nominations(session: Session) -> list[Nominations]:
    """Get all nominations from the database."""
    try:
        query = select(Nominations)
        result = session.execute(query).scalars().all()
        return list(result)
    except Exception as e:
        LOGGER.error(f"Error retrieving nominations: {e!s}")
        return []


def get_user_nominations(session: Session, user_id: int) -> list[Nominations]:
    """Get all nominations from a specific user.

    Parameters
    ----------
    session: Session
        The database session
    user_id: int
        The Discord user ID to get nominations for

    Returns
    -------
    list[Nominations]
        A list of the user's nominations
    """
    try:
        query = select(Nominations).where(Nominations.user_id == user_id)
        result = session.execute(query).scalars().all()
        return list(result)
    except Exception as e:
        LOGGER.error(f"Error retrieving nominations for user {user_id}: {e!s}")
        return []


def clear_all_nominations(session: Session) -> int:
    """Clear all nominations from the database.

    Returns
    -------
    int
        The number of nominations cleared
    """
    try:
        stmt = delete(Nominations)
        result = session.execute(stmt)
        return result.rowcount
    except Exception as e:
        LOGGER.error(f"Error clearing nominations: {e!s}")
        return 0
