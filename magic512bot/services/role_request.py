from sqlalchemy import select
from sqlalchemy.orm import Session

from magic512bot.config import LOGGER
from magic512bot.models.user import User


def get_user_sweat_roles(session: Session, user_id: int) -> list[str]:
    try:
        query = select(User.sweat_roles).where(User.id == user_id)
        result = session.execute(query).scalar_one_or_none()
        return result if result is not None else []
    except Exception as e:
        LOGGER.error(f"Error querying sweat roles for user {user_id}: {e!s}")
        raise


def add_user_sweat_role(session: Session, user_id: int, role_name: str) -> None:
    """Add a role to user's sweat_roles in database."""
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()

    if user:
        if user.sweat_roles is None:
            user.sweat_roles = []
        if role_name not in user.sweat_roles:
            user.sweat_roles.append(role_name)
    else:
        user = User(id=user_id, sweat_roles=[role_name])
        session.add(user)


def add_user_sweat_roles(
    session: Session, user_id: int, user_name: str, roles: list[str]
) -> None:
    """Add roles to user's sweat_roles in database."""
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()

    if user:
        if user.sweat_roles is None:
            user.sweat_roles = []
        for role_name in roles:
            if role_name not in user.sweat_roles:
                user.sweat_roles.append(role_name)
    else:
        LOGGER.info("Creating new user")
        user = User(id=user_id, user_name=user_name, sweat_roles=roles)
        session.add(user)


def remove_user_sweat_roles(
    session: Session, user_id: int, user_name: str, roles: list[str]
):
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()
    roles_to_remove = set(roles)
    if user:
        if user.sweat_roles is None:
            LOGGER.error("User has no sweat roles")
        user.sweat_roles = [
            role for role in user.sweat_roles if role not in roles_to_remove
        ]
    else:
        LOGGER.info("Unable to find user")
        return
