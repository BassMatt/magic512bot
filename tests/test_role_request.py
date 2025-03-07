from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from magic512bot.cogs.role_request import (
    ALLOWED_ROLE_REQUESTS,
    RoleRequest,
    Roles,
    _process_user_milestone_roles,
    _sync_user_sweat_roles,
)


@pytest.mark.asyncio
async def test_give_monarch(mock_bot, mock_interaction, mock_member):
    """Test the give_monarch command."""
    cog = RoleRequest(mock_bot)

    # Setup the test
    mock_role = MagicMock(spec=discord.Role)
    mock_role.name = Roles.THE_MONARCH
    mock_role.mention = f"<@&{Roles.THE_MONARCH}>"

    # Create a proper Member mock that will pass the isinstance check
    mock_user = MagicMock(spec=discord.Member)
    mock_user.roles = [mock_role]
    mock_user.remove_roles = AsyncMock()
    mock_user.display_name = "Test User"
    mock_user.mention = "<@12345>"

    # Replace the interaction.user with our proper Member mock
    mock_interaction.user = mock_user

    # Ensure the guild has the role
    mock_interaction.guild.roles = [mock_role]
    mock_interaction.guild.get_role = MagicMock(return_value=mock_role)

    # Mock discord.utils.get to return our mock role
    with patch("discord.utils.get", return_value=mock_role):
        # Call the callback method directly
        await cog.give_monarch.callback(cog, mock_interaction, mock_member)

        # Verify the expected actions were taken
        mock_user.remove_roles.assert_called_once_with(
            mock_role,
            reason=f"Monarch transfer initiated by {mock_user.display_name}",
        )
        mock_member.add_roles.assert_called_once_with(
            mock_role,
            reason=f"Monarch transfer initiated by {mock_user.display_name}",
        )
        mock_interaction.response.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_role_autocomplete(mock_bot, mock_interaction):
    """Test the role_autocomplete method."""
    cog = RoleRequest(mock_bot)

    # Call the role_autocomplete method directly (not a command)
    result = await cog.role_autocomplete(mock_interaction, "sweat")

    # Verify the result contains sweat roles
    assert len(result) > 0
    for choice in result:
        assert "sweat" in choice.name.lower()


@pytest.mark.asyncio
async def test_request_role(mock_bot, mock_interaction):
    """Test the request_role command."""
    cog = RoleRequest(mock_bot)

    # Setup the test
    mock_role = MagicMock(spec=discord.Role)
    mock_role.name = "Standard Sweat"
    mock_role.id = 1333297150192259112
    mock_role.mention = "<@&1333297150192259112>"

    # Create a proper Member mock
    mock_user = MagicMock(spec=discord.Member)
    mock_user.id = 12345
    mock_user.roles = []
    mock_user.mention = "<@12345>"
    mock_interaction.user = mock_user

    # Setup guild
    mock_interaction.guild.roles = [mock_role]

    # Mock the channel as a TextChannel
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()

    # Patch ROLE_REQUEST_CHANNEL_ID
    with patch("magic512bot.cogs.role_request.ROLE_REQUEST_CHANNEL_ID", 12345):
        # Patch get_channel to return our mock channel
        mock_interaction.guild.get_channel = MagicMock(return_value=mock_channel)

        # Patch ALLOWED_ROLE_REQUESTS to include our test role
        with patch(
            "magic512bot.cogs.role_request.ALLOWED_ROLE_REQUESTS",
            {"Standard Sweat": mock_role.id},
        ):
            # Mock discord.utils.get to return our mock role
            with patch("discord.utils.get", return_value=mock_role):
                # Mock RoleRequestView
                with patch(
                    "magic512bot.cogs.role_request.RoleRequestView"
                ) as mock_view_class:
                    mock_view = MagicMock()
                    mock_view_class.return_value = mock_view

                    # Mock Embed
                    with patch("discord.Embed") as mock_embed_class:
                        mock_embed = MagicMock()
                        mock_embed_class.return_value = mock_embed

                        # Call the callback method directly
                        await cog.request_role.callback(
                            cog, mock_interaction, "Standard Sweat", "I earned it"
                        )

                        # Verify the expected actions were taken
                        mock_channel.send.assert_called_once()
                        mock_interaction.response.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_bootstrap_db(mock_bot, mock_interaction):
    """Test the bootstrap_db command."""
    cog = RoleRequest(mock_bot)

    # Mock the guild members
    member1 = MagicMock(spec=discord.Member)
    member1.bot = False
    member2 = MagicMock(spec=discord.Member)
    member2.bot = True  # Bot should be skipped
    mock_interaction.guild.members = [member1, member2]

    # Mock _sync_user_sweat_roles
    with patch(
        "magic512bot.cogs.role_request._sync_user_sweat_roles", return_value=set()
    ):
        # Access the callback directly
        await cog.bootstrap_db.callback(cog, mock_interaction)

        # Verify that the response was sent
        mock_interaction.response.send_message.assert_called_once()

        # Verify that _sync_user_sweat_roles was called for non-bot members
        from magic512bot.cogs.role_request import _sync_user_sweat_roles

        _sync_user_sweat_roles.assert_called_once_with(member1, mock_bot.db)


@pytest.mark.asyncio
async def test_sweat_leaderboard(mock_bot, mock_interaction):
    """Test the sweat_leaderboard command."""
    cog = RoleRequest(mock_bot)

    # Setup mock members with roles
    member1 = MagicMock(spec=discord.Member)
    member1.bot = False
    role1 = MagicMock(spec=discord.Role)
    role1.name = "Standard Sweat"
    role2 = MagicMock(spec=discord.Role)
    role2.name = "Modern Sweat"
    member1.roles = [role1, role2]
    member1.display_name = "Member1"
    member1.mention = "<@123>"

    member2 = MagicMock(spec=discord.Member)
    member2.bot = False
    member2.roles = [role1]
    member2.display_name = "Member2"
    member2.mention = "<@456>"

    # Add members to the guild
    mock_interaction.guild.members = [member1, member2]

    # Mock SWEAT_ROLES to include our test roles
    with patch(
        "magic512bot.cogs.role_request.SWEAT_ROLES",
        {"Standard Sweat": 1, "Modern Sweat": 2},
    ):
        # Call the callback method directly
        await cog.sweat_leaderboard.callback(cog, mock_interaction)

        # Verify a response was sent
        mock_interaction.response.send_message.assert_called_once()


def test_sync_user_sweat_roles(mock_member, db_session):
    """Test the _sync_user_sweat_roles function."""
    # Create a mock sessionmaker that returns our test session
    mock_sessionmaker = MagicMock()
    mock_sessionmaker.begin.return_value.__enter__.return_value = db_session

    # Mock the member's roles
    role1 = MagicMock(spec=discord.Role)
    role1.name = "Standard Sweat"
    role2 = MagicMock(spec=discord.Role)
    role2.name = "Modern Sweat"
    mock_member.roles = [role1, role2]

    # Mock get_user_sweat_roles to return an empty list
    with patch("magic512bot.cogs.role_request.get_user_sweat_roles", return_value=[]):
        # Call _sync_user_sweat_roles
        result = _sync_user_sweat_roles(mock_member, mock_sessionmaker)

        # Verify the result
        assert "Standard Sweat" in result
        assert "Modern Sweat" in result


@pytest.mark.asyncio
async def test_process_user_milestone_roles(mock_member, db_session):
    """Test the _process_user_milestone_roles function."""
    # Create a mock sessionmaker that returns our test session
    mock_sessionmaker = MagicMock()
    mock_sessionmaker.begin.return_value.__enter__.return_value = db_session

    # Mock the guild
    mock_guild = MagicMock()

    # Mock get_user_sweat_roles to return 8 roles (enough for OmniSweat)
    with patch(
        "magic512bot.cogs.role_request.get_user_sweat_roles",
        return_value=[
            "Role1",
            "Role2",
            "Role3",
            "Role4",
            "Role5",
            "Role6",
            "Role7",
            "Role8",
        ],
    ):
        # Mock the guild.get_role function
        omni_role = MagicMock(spec=discord.Role)
        mock_guild.get_role = MagicMock(return_value=omni_role)

        # Call _process_user_milestone_roles
        await _process_user_milestone_roles(mock_member, mock_guild, mock_sessionmaker)

        # Verify that the role was added
        mock_member.add_roles.assert_called_once_with(omni_role)

        # Verify that the DM was sent
        mock_member.send.assert_called_once()
        message = mock_member.send.call_args[0][0]
        assert "Omni Sweat" in message
