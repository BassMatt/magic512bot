from collections.abc import Callable
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest
from discord import app_commands

from magic512bot.cogs.role_request import (
    RoleRequest,
    Roles,
)
from magic512bot.config import LOGGER


@pytest.mark.asyncio
async def test_give_monarch(
    mock_bot: MagicMock,
    mock_interaction: discord.Interaction,
    mock_member: discord.Member,
) -> None:
    """Test the give_monarch command."""
    cog = RoleRequest(mock_bot)

    # Setup the test
    mock_role = MagicMock(spec=discord.Role)
    mock_role.name = Roles.THE_MONARCH
    mock_role.mention = f"<@&{Roles.THE_MONARCH}>"

    # Create a proper Member mock that will pass the isinstance check
    mock_user = MagicMock(spec=discord.Member)
    type(mock_user).roles = PropertyMock(return_value=[mock_role])
    mock_user.remove_roles = AsyncMock()
    mock_user.display_name = "Test User"
    mock_user.mention = "<@12345>"

    # Replace the interaction.user with our proper Member mock
    mock_interaction.user = mock_user

    # Set up the guild mock
    guild_mock = cast(discord.Guild, mock_interaction.guild)
    with patch.object(
        type(guild_mock), "roles", new_callable=PropertyMock
    ) as mock_roles:
        mock_roles.return_value = [mock_role]
        with patch.object(guild_mock, "get_role") as mock_get_role:
            mock_get_role.return_value = mock_role

            # Mock discord.utils.get to return our mock role
            with patch("discord.utils.get", return_value=mock_role):
                # Cast the command to the correct type and get its callback
                give_monarch_command = cast(app_commands.Command, cog.give_monarch)
                callback = cast(
                    Callable[[Any, discord.Interaction, discord.Member], Any],
                    give_monarch_command.callback,
                )
                await callback(cog, mock_interaction, mock_member)

                # Verify the expected actions were taken
                mock_remove_roles = cast(AsyncMock, mock_user.remove_roles)
                mock_add_roles = cast(AsyncMock, mock_member.add_roles)
                mock_send = cast(AsyncMock, mock_interaction.response.send_message)

                assert mock_remove_roles.await_count == 1
                assert mock_add_roles.await_count == 1
                assert mock_send.await_count == 1


@pytest.mark.asyncio
async def test_role_autocomplete(
    mock_bot: MagicMock,
    mock_interaction: discord.Interaction,
) -> None:
    """Test the role_autocomplete method."""
    cog = RoleRequest(mock_bot)

    # Call the role_autocomplete method directly (not a command)
    result = await cog.role_autocomplete(mock_interaction, "sweat")

    # Verify the result contains sweat roles
    assert len(result) > 0
    for choice in result:
        assert "sweat" in choice.name.lower()


@pytest.mark.asyncio
async def test_request_role(
    mock_bot: MagicMock,
    mock_interaction: discord.Interaction,
) -> None:
    """Test the request_role command."""
    LOGGER.info("Starting request_role test")
    cog = RoleRequest(mock_bot)

    # Setup with proper types
    mock_role = MagicMock(spec=discord.Role)
    mock_role.name = "Standard Sweat"
    mock_role.id = 1333297150192259112
    mock_role.mention = "<@&1333297150192259112>"
    LOGGER.debug(f"Created mock role: {mock_role.name} ({mock_role.id})")

    mock_user = MagicMock(spec=discord.Member)
    mock_user.id = 12345
    type(mock_user).roles = PropertyMock(return_value=[])
    mock_user.mention = "<@12345>"
    mock_interaction.user = cast(discord.Member, mock_user)
    LOGGER.debug(f"Created mock user: {mock_user.mention}")

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    LOGGER.debug("Created mock channel")

    guild_mock: Any = mock_interaction.guild
    with patch.object(
        type(guild_mock),
        "roles",
        new_callable=PropertyMock,
        return_value=[mock_role],
    ):
        LOGGER.debug("Patched guild roles")
        guild_mock.get_channel = MagicMock(
            return_value=cast(discord.TextChannel, mock_channel)
        )
        LOGGER.info("Calling request_role command")
        # Get the unbound method and call it with self
        callback: Callable[[RoleRequest, discord.Interaction, str, str], Any] = (
            cog.request_role.callback
        )

        # Call with self (cog) as first argument
        await callback(
            cog,  # Pass self (the cog instance)
            mock_interaction,  # Pass interaction
            "Standard Sweat",  # Pass role name
            "I want to participate in Standard events",  # Pass reason
        )

        # Verify interactions
        mock_interaction.response.send_message.assert_called_once()
        mock_channel.send.assert_awaited_once()
        LOGGER.info("Test completed successfully")


@pytest.mark.asyncio
async def test_sweat_leaderboard(
    mock_interaction: discord.Interaction,
) -> None:
    """Test the sweat leaderboard command."""
    # Create a proper bot mock
    mock_bot = MagicMock()
    mock_bot.db = MagicMock()
    cog = RoleRequest(mock_bot)

    # Create mock roles with proper name attribute setup
    modern_sweat = MagicMock(spec=discord.Role)
    modern_sweat.name = "Modern Sweat"
    legacy_sweat = MagicMock(spec=discord.Role)
    legacy_sweat.name = "Legacy Sweat"
    normal_role = MagicMock(spec=discord.Role)
    normal_role.name = "Not a sweat role"

    # Create mock members with different numbers of sweat roles
    member1 = MagicMock(spec=discord.Member)
    member1.display_name = "Alpha"
    member1.bot = False
    type(member1).roles = PropertyMock(return_value=[modern_sweat, legacy_sweat])

    member2 = MagicMock(spec=discord.Member)
    member2.display_name = "Beta"
    member2.bot = False
    type(member2).roles = PropertyMock(return_value=[modern_sweat])

    member3 = MagicMock(spec=discord.Member)
    member3.display_name = "Charlie"
    member3.bot = False
    type(member3).roles = PropertyMock(return_value=[normal_role])

    # Set up the guild mock
    guild_mock = cast(discord.Guild, mock_interaction.guild)
    with patch.object(
        type(guild_mock), "members", new_callable=PropertyMock
    ) as mock_members_prop:
        mock_members_prop.return_value = [member1, member2, member3]

        # Cast the command to the correct type and get its callback
        sweat_leaderboard_command = cast(app_commands.Command, cog.sweat_leaderboard)
        callback = cast(
            Callable[[Any, discord.Interaction], Any],
            sweat_leaderboard_command.callback,
        )
        await callback(cog, mock_interaction)

        # Verify the response
        mock_send = cast(AsyncMock, mock_interaction.response.send_message)
        assert mock_send.await_count == 1

        # Get the embed from the call arguments
        send_message_call = mock_send.await_args_list[0]
        embed = send_message_call[1]["embed"]

        # Verify embed contents
        assert "Sweat Role Leaderboard" in embed.title
        assert "**2 roles**: **Alpha**" in embed.description
        assert "**1 role**: **Beta**" in embed.description
        assert embed.color == discord.Color.blue()


@pytest.mark.asyncio
async def test_sweat_leaderboard_no_roles(
    mock_interaction: discord.Interaction,
) -> None:
    """Test the sweat leaderboard command when no one has sweat roles."""
    # Create a proper bot mock
    mock_bot = MagicMock()
    mock_bot.db = MagicMock()
    cog = RoleRequest(mock_bot)

    # Create mock member with no sweat roles
    member = MagicMock(spec=discord.Member)
    member.bot = False
    type(member).roles = PropertyMock(return_value=[MagicMock(name="Not a sweat role")])

    # Set up the guild mock
    guild_mock = cast(discord.Guild, mock_interaction.guild)
    with patch.object(
        type(guild_mock), "members", new_callable=PropertyMock
    ) as mock_members_prop:
        mock_members_prop.return_value = [member]

        # Cast the command to the correct type and get its callback
        sweat_leaderboard_command = cast(app_commands.Command, cog.sweat_leaderboard)
        callback = cast(
            Callable[[Any, discord.Interaction], Any],
            sweat_leaderboard_command.callback,
        )
        await callback(cog, mock_interaction)

        # Verify the response
        mock_send = cast(AsyncMock, mock_interaction.response.send_message)
        assert mock_send.await_count == 1

        # Get the embed from the call arguments
        send_message_call = mock_send.await_args_list[0]
        embed = send_message_call[1]["embed"]

        # Verify embed contents
        assert "No sweat roles found!" in embed.description


class MemberMock(MagicMock):
    """Custom mock class for Discord Member."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._roles: list[discord.Role] = []
        self.add_roles = AsyncMock()
        self.remove_roles = AsyncMock()
        self.send = AsyncMock()

    @property
    def roles(self) -> list[discord.Role]:
        """Get the roles list."""
        return self._roles

    @roles.setter
    def roles(self, value: list[discord.Role]) -> None:
        """Set the roles list."""
        self._roles = value
