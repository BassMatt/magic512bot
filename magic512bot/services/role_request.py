from typing import List

from models.User import User  # Assuming you have this model
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_user_roles(session: Session, user_id: int) -> List[str]:
    query = select(User.roles).where(
        User.user_id == user_id,
    )

    # Execute query and fetch all results
    result = session.execute(query)

    # Extract role_names from result
    role_names = [row[0] for row in result.fetchall()]

    return role_names


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
        if user.sweat_roles is None:
            user.sweat_roles = []
        for role_name in roles:
            if role_name not in user.sweat_roles:
                user.sweat_roles.append(role_name)
    else:
        user = User(id=user_id, user_name=user_name, sweat_roles=roles)
        session.add(user)


def remove_role_from_user(session: Session, user_id: int, role_id: int) -> None:
    """Remove a role from user's roles in database."""
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()

    if user and user.roles and role_id in user.roles:
        user.roles.remove(role_id)
