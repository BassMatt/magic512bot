from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from magic512bot.config import LOGGER
from magic512bot.models.nomination import Nomination

MAX_NOMINATION_LENGTH = 55


def add_nomination(session: Session, user_id: int, format: str) -> None:
    """
    Add a nomination for a user.

    Args:
        session: The database session
        user_id: The Discord user ID
        format: The format being nominated

    Raises:
        ValueError: If the format is too long
    """
    # Validate format length
    if len(format) > MAX_NOMINATION_LENGTH:
        raise ValueError("Format is too long. Please keep it under 55 characters.")

    try:
        # Check if the format is already nominated
        stmt = select(Nomination).where(Nomination.format == format)
        result = session.execute(stmt)
        existing = result.scalars().first()

        if not existing:
            # Create new nomination
            nomination = Nomination(user_id=user_id, format=format)
            session.add(nomination)
    except Exception as e:
        LOGGER.error(f"Error adding nomination for user {user_id}: {e!s}")
        raise


def get_all_nominations(session: Session) -> list[Nomination]:
    """Get all nominations from the database."""
    try:
        query = select(Nomination)
        result = session.execute(query).scalars().all()
        return list(result)
    except Exception as e:
        LOGGER.error(f"Error retrieving nominations: {e!s}")
        return []


def get_user_nominations(session: Session, user_id: int) -> list[Nomination]:
    """Get all nominations from a specific user.

    Parameters
    ----------
    session: Session
        The database session
    user_id: int
        The Discord user ID to get nominations for

    Returns
    -------
    list[Nomination]
        A list of the user's nominations
    """
    try:
        query = select(Nomination).where(Nomination.user_id == user_id)
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
        stmt = delete(Nomination)
        result = session.execute(stmt)
        return result.rowcount
    except Exception as e:
        LOGGER.error(f"Error clearing nominations: {e!s}")
        return 0
