from typing import List

from config import LOGGER
from models.user import User
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_user_roles(session: Session, user_id: int) -> List[str]:
    try:
        query = select(User.roles).where(
            User.id == user_id,
        )
        # Execute query and fetch all results
        if result := session.execute(query).scalar_one_or_none():
            return result
        return []
    except Exception as e:
        LOGGER.error(f"Error querying roles for user {user_id}: {str(e)}")
        raise


def add_role_to_user(session: Session, user_id: int, role_name: str) -> None:
    """Add a role to user's roles in database."""
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()

    if user:
        if user.roles is None:
            user.roles = []
        if role_name not in user.roles:
            user.roles.append(role_name)
    else:
        user = User(id=user_id, roles=[role_name])
        session.add(user)


def add_roles_to_user(
    session: Session, user_id: int, user_name: str, roles: list[str]
) -> None:
    """Add a role to user's roles in database."""
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()

    if user:
        if user.roles is None:
            user.roles = []
        for role_name in roles:
            if role_name not in user.roles:
                user.roles.append(role_name)
    else:
        LOGGER.info("Creating new user")
        user = User(id=user_id, user_name=user_name, roles=roles)
        session.add(user)


def remove_roles_from_user(
    session: Session, user_id: int, user_name: str, roles: list[str]
):
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()
    roles_to_remove = set(roles)
    if user:
        if user.roles is None:
            LOGGER.error("User has no roles")
        user.roles = [role for role in user.roles if roles not in roles_to_remove]
    else:
        LOGGER.info("Unable to find user")
        return
