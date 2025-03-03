from typing import Set

import discord
from config import LOGGER
from services.role_request import (
    add_user_sweat_roles,
    get_user_sweat_roles,
    remove_user_sweat_roles,
)
from sqlalchemy.orm import Session, sessionmaker

from role_request import MILESTONE_ROLES, SWEAT_ROLES, Roles


def sync_user_sweat_roles(
    member: discord.Member, db: sessionmaker[Session]
) -> Set[str]:
    """
    Want to treat user's Discord roles as source of truth incase bot goes down,
    or want to manually add for whatever reason.

    So, syncing necessary to ensure state is up to date.

    Returns the current list of roles for the user after sync
    """
    user_db_sweat_roles = None
    LOGGER.info("Getting Users DB Roles")
    with db.begin() as session:
        user_db_sweat_roles = set(
            get_user_sweat_roles(session=session, user_id=member.id)
        )

    LOGGER.info(f"{len(user_db_sweat_roles)} Users DB Roles Found")
    sweat_db_roles_to_add: list[str] = []
    sweat_db_roles_to_remove: list[str] = []

    # 1. Read-Repair on the Sweat Role Database
    user_sweat_roles = [
        role.name for role in member.roles if role.name in SWEAT_ROLES.keys()
    ]
    for role in user_sweat_roles:
        if role not in user_db_sweat_roles:
            sweat_db_roles_to_add.append(role)
    for sweat_db_role in user_db_sweat_roles:
        if sweat_db_role not in user_sweat_roles:
            sweat_db_roles_to_remove.append(sweat_db_role)

    # 3. Sync DB_Roles and Member Roles
    LOGGER.info(f"Adding {len(sweat_db_roles_to_add)} roles to user)")
    with db.begin() as session:
        if len(sweat_db_roles_to_remove) > 0:
            remove_user_sweat_roles(
                session, member.id, member.name, sweat_db_roles_to_remove
            )
        add_user_sweat_roles(session, member.id, member.name, sweat_db_roles_to_add)
    LOGGER.info("Finished adding db_roles to User")
    user_db_sweat_roles.update(sweat_db_roles_to_add)

    return user_db_sweat_roles


async def _clear_user_sweat_milestones(member: discord.Member):
    for role in member.roles:
        if role.name in MILESTONE_ROLES.keys():
            await member.remove_roles(role)


async def process_user_milestone_roles(
    member: discord.Member, guild: discord.Guild, db: sessionmaker[Session]
):
    sweat_role_count = 0
    with db.begin() as session:
        user_sweat_roles = get_user_sweat_roles(session=session, user_id=member.id)
        sweat_role_count = len(user_sweat_roles)

    # Add Milestone ROle, if necessary
    LOGGER.info(f"User Sweat Role Count is now {sweat_role_count}")
    if sweat_role_count >= 8:
        if any(role.name == Roles.OMNI_SWEAT for role in member.roles):
            return
        await _clear_user_sweat_milestones(member)
        if omnisweat_role := guild.get_role(MILESTONE_ROLES[Roles.OMNI_SWEAT]):
            await member.add_roles(omnisweat_role)
            await member.send(
                "Congratulations! You're now a Sweat Knight. "
                + "Fear not, the blacksmith can surely add "
                + "more ventilation holes!"
            )
    elif sweat_role_count >= 5 and sweat_role_count < 8:
        if any(role.name == Roles.SWEAT_LORD for role in member.roles):
            return
        await _clear_user_sweat_milestones(member)
        if sweat_lord_role := guild.get_role(MILESTONE_ROLES[Roles.SWEAT_LORD]):
            await member.add_roles(sweat_lord_role)
            await member.send(
                "Congratulations! You're now a Sweat Lord. "
                + "Lo, thou hast transformed thy noble throne "
                + "into quite the splash zone"
            )
    elif sweat_role_count >= 3:
        if any(role.name == Roles.SWEAT_KNIGHT for role in member.roles):
            return
        await _clear_user_sweat_milestones(member)
        if sweat_knight_role := guild.get_role(MILESTONE_ROLES[Roles.SWEAT_KNIGHT]):
            await member.add_roles(sweat_knight_role)
            await member.send(
                "As it was foretold in the Damp Scrolls of Destiny! "
                + "Look how you glisten with otherworldly radiance! "
                + "The heavens themselves open to welcome their"
                + " new moistened master!"
                + "YOU ARE NOW AN OMNISWEAT"
            )
