import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from magic512bot.cogs.nominations import Nominations


@pytest.mark.asyncio
async def test_nominate_command_success(mock_bot, mock_interaction):
    """Test the nominate command when successful."""
    cog = Nominations(mock_bot)
    cog.can_nominate = True  # Allow nominations

    # Mock the get_user_nominations function to return an empty list
    with patch("magic512bot.cogs.nominations.get_user_nominations", return_value=[]):
        # Mock the add_nomination function
        with patch("magic512bot.cogs.nominations.add_nomination"):
            # Call the nominate method's callback directly
            await cog.nominate.callback(cog, mock_interaction, "Modern")

            # Verify the response was sent
            mock_interaction.response.send_message.assert_called_once()

            # Verify the message contains the format name
            message = mock_interaction.response.send_message.call_args[0][0]
            assert "Modern" in message
            assert "✅" in message


@pytest.mark.asyncio
async def test_nominate_command_not_open(mock_bot, mock_interaction):
    """Test the nominate command when nominations are not open."""
    cog = Nominations(mock_bot)
    cog.can_nominate = False  # Nominations are closed

    # Call the nominate method directly
    await cog.nominate.callback(cog, mock_interaction, "Modern")

    # Verify the response was sent
    mock_interaction.response.send_message.assert_called_once()

    # Verify the message indicates nominations are closed
    message = mock_interaction.response.send_message.call_args[0][0]
    assert "not currently open" in message


@pytest.mark.asyncio
async def test_nominate_command_max_nominations(mock_bot, mock_interaction):
    """Test the nominate command when user has reached max nominations."""
    cog = Nominations(mock_bot)
    cog.can_nominate = True  # Allow nominations

    # Mock the get_user_nominations function to return 2 nominations
    with patch(
        "magic512bot.cogs.nominations.get_user_nominations",
        return_value=[MagicMock(), MagicMock()],
    ):
        # Call the nominate method directly
        await cog.nominate.callback(cog, mock_interaction, "Modern")

        # Verify the response was sent
        mock_interaction.response.send_message.assert_called_once()

        # Verify the message indicates max nominations reached
        message = mock_interaction.response.send_message.call_args[0][0]
        assert "maximum of 2 nominations" in message


@pytest.mark.asyncio
async def test_nominate_command_error(mock_bot, mock_interaction):
    """Test the nominate command when an error occurs."""
    cog = Nominations(mock_bot)
    cog.can_nominate = True  # Allow nominations

    # Mock the get_user_nominations function to return an empty list
    with patch("magic512bot.cogs.nominations.get_user_nominations", return_value=[]):
        # Mock the add_nomination function to raise an error
        with patch(
            "magic512bot.cogs.nominations.add_nomination",
            side_effect=ValueError("Test error"),
        ):
            # Call the nominate method directly
            await cog.nominate.callback(cog, mock_interaction, "Modern")

            # Verify the response was sent
            mock_interaction.response.send_message.assert_called_once()

            # Verify the message contains the error
            message = mock_interaction.response.send_message.call_args[0][0]
            assert "❌" in message
            assert "Test error" in message


@pytest.mark.asyncio
async def test_nominate_command_exception(mock_bot, mock_interaction):
    """Test the nominate command when an unexpected exception occurs."""
    cog = Nominations(mock_bot)
    cog.can_nominate = True  # Allow nominations

    # Mock the get_user_nominations function to return an empty list
    with patch("magic512bot.cogs.nominations.get_user_nominations", return_value=[]):
        # Mock the add_nomination function to raise an exception
        with patch(
            "magic512bot.cogs.nominations.add_nomination",
            side_effect=Exception("Unexpected error"),
        ):
            # Call the nominate method directly
            await cog.nominate.callback(cog, mock_interaction, "Modern")

            # Verify the response was sent
            mock_interaction.response.send_message.assert_called_once()

            # Verify the message indicates an error
            message = mock_interaction.response.send_message.call_args[0][0]
            assert "❌" in message
            assert "error" in message.lower()


@pytest.mark.asyncio
async def test_daily_check_thursday(mock_bot):
    """Test the daily_check method on Thursday."""
    cog = Nominations(mock_bot)

    # Mock datetime.datetime.now to return a Thursday
    thursday = datetime.datetime(2023, 3, 9)  # A Thursday
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = thursday
        mock_datetime.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)

        # Mock the open_nominations method
        cog.open_nominations = AsyncMock()

        # Call the daily_check method
        await cog.daily_check()

        # Verify open_nominations was called
        cog.open_nominations.assert_called_once()

        # Verify the last_thursday_run was updated
        assert cog.last_thursday_run == thursday.date()


@pytest.mark.asyncio
async def test_daily_check_sunday(mock_bot):
    """Test the daily_check method on Sunday."""
    cog = Nominations(mock_bot)

    # Mock datetime.datetime.now to return a Sunday
    sunday = datetime.datetime(2023, 3, 12)  # A Sunday
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = sunday
        mock_datetime.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)

        # Mock the create_poll method
        cog.create_poll = AsyncMock()

        # Call the daily_check method
        await cog.daily_check()

        # Verify create_poll was called
        cog.create_poll.assert_called_once()

        # Verify the last_sunday_run was updated
        assert cog.last_sunday_run == sunday.date()


@pytest.mark.asyncio
async def test_daily_check_already_run(mock_bot):
    """Test the daily_check method when it has already run today."""
    cog = Nominations(mock_bot)

    # Mock datetime.datetime.now to return a Thursday
    thursday = datetime.datetime(2023, 3, 9)  # A Thursday
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = thursday
        mock_datetime.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)

        # Set last_thursday_run to today
        cog.last_thursday_run = thursday.date()

        # Mock the open_nominations method
        cog.open_nominations = AsyncMock()

        # Call the daily_check method
        await cog.daily_check()

        # Verify open_nominations was not called
        cog.open_nominations.assert_not_called()


@pytest.mark.asyncio
async def test_daily_check_other_day(mock_bot):
    """Test the daily_check method on a day that's not Thursday or Sunday."""
    cog = Nominations(mock_bot)

    # Mock datetime.datetime.now to return a Monday
    monday = datetime.datetime(2023, 3, 6)  # A Monday
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = monday
        mock_datetime.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)

        # Mock the methods
        cog.open_nominations = AsyncMock()
        cog.create_poll = AsyncMock()

        # Call the daily_check method
        await cog.daily_check()

        # Verify neither method was called
        cog.open_nominations.assert_not_called()
        cog.create_poll.assert_not_called()


@pytest.mark.asyncio
async def test_open_nominations(mock_bot):
    """Test the open_nominations method."""
    cog = Nominations(mock_bot)

    # Create a proper mock channel with the correct spec
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_bot.get_channel.return_value = mock_channel

    # Call the open_nominations method
    await cog.open_nominations()

    # Verify the channel.send was called
    mock_channel.send.assert_called_once()

    # Verify can_nominate was set to True
    assert cog.can_nominate is True


@pytest.mark.asyncio
async def test_open_nominations_channel_not_found(mock_bot):
    """Test the open_nominations method when the channel is not found."""
    cog = Nominations(mock_bot)

    # Mock the get_channel to return None
    mock_bot.get_channel.return_value = None

    # Call the open_nominations method
    await cog.open_nominations()

    # Verify can_nominate was not changed
    assert cog.can_nominate is False


@pytest.mark.asyncio
async def test_create_poll_no_nominations(mock_bot):
    """Test the create_poll method when there are no nominations."""
    cog = Nominations(mock_bot)

    # Create a proper mock channel
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_bot.get_channel.return_value = mock_channel

    # Mock get_all_nominations to return an empty list
    with patch("magic512bot.cogs.nominations.get_all_nominations", return_value=[]):
        # Call the create_poll method
        await cog.create_poll()

        # Verify the channel.send was called with the no nominations message
        mock_channel.send.assert_called_once_with(
            "No nominations were submitted this week."
        )

        # Verify can_nominate was not changed
        assert cog.can_nominate is False


@pytest.mark.asyncio
async def test_create_poll_with_nominations(mock_bot):
    """Test the create_poll method with nominations."""
    cog = Nominations(mock_bot)

    # Create a proper mock channel
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_bot.get_channel.return_value = mock_channel

    # Create mock nominations
    mock_nomination1 = MagicMock()
    mock_nomination1.format = "modern"
    mock_nomination2 = MagicMock()
    mock_nomination2.format = "standard"

    # Mock get_all_nominations to return our mock nominations
    with patch(
        "magic512bot.cogs.nominations.get_all_nominations",
        return_value=[mock_nomination1, mock_nomination2],
    ):
        # Mock clear_all_nominations
        with patch("magic512bot.cogs.nominations.clear_all_nominations"):
            # Create a mock poll message
            mock_poll_message = MagicMock()
            mock_poll_message.id = "test_poll_id"

            # Mock the Poll constructor and send method
            mock_poll = MagicMock()
            with patch("discord.Poll", return_value=mock_poll):
                # Mock the channel.send to return our mock message
                mock_channel.send.return_value = mock_poll_message

                # Call the create_poll method
                await cog.create_poll()

                # Verify the channel.send was called
                mock_channel.send.assert_called_once()

                # Verify can_nominate was set to False
                assert cog.can_nominate is False


@pytest.mark.asyncio
async def test_on_poll_end_not_our_poll(mock_bot):
    """Test the on_poll_end method when it's not our poll."""
    cog = Nominations(mock_bot)
    cog.active_poll_id = "our_poll_id"

    # Create a mock poll with a different ID
    mock_poll = MagicMock()
    mock_poll.message = MagicMock()
    mock_poll.message.id = "different_poll_id"

    # Call the on_poll_end method
    await cog.on_poll_end(mock_poll)

    # Verify nothing happened
    assert cog.active_poll_id == "our_poll_id"


@pytest.mark.asyncio
async def test_on_poll_end_our_poll(mock_bot):
    """Test the on_poll_end method when it's our poll."""
    cog = Nominations(mock_bot)
    cog.active_poll_id = "test_poll_id"

    # Create a mock poll with our ID
    mock_poll = MagicMock()
    mock_poll.message = MagicMock()
    mock_poll.message.id = "test_poll_id"
    mock_poll.victor_answer = MagicMock()

    # Use the same format as in the actual implementation
    formatted_text = "**Modern**"
    expected_text = "Modern"  # What we expect after stripping
    mock_poll.victor_answer.text = formatted_text

    # Mock the create_event_for_format method
    cog.create_event_for_format = AsyncMock()

    # Call the on_poll_end method
    await cog.on_poll_end(mock_poll)

    # Check what was actually passed
    actual_arg = cog.create_event_for_format.call_args[0][0]

    # Print for debugging
    print(f"Expected: '{expected_text}'")
    print(f"Actual: '{actual_arg}'")

    # Verify create_event_for_format was called with the stripped text
    assert actual_arg == expected_text, (
        f"Expected '{expected_text}' but got '{actual_arg}'"
    )


@pytest.mark.asyncio
async def test_on_poll_end_no_victor(mock_bot):
    """Test the on_poll_end method when there is no victor."""
    cog = Nominations(mock_bot)
    cog.active_poll_id = "test_poll_id"

    # Create a mock poll with our ID but no victor
    mock_poll = MagicMock()
    mock_poll.message = MagicMock()
    mock_poll.message.id = "test_poll_id"
    mock_poll.victor_answer = None

    # Mock the send_error_message method
    mock_bot.send_error_message = AsyncMock()

    # Call the on_poll_end method
    await cog.on_poll_end(mock_poll)

    # Verify send_error_message was called
    mock_bot.send_error_message.assert_called_once()

    # Verify active_poll_id was reset
    assert cog.active_poll_id is None


@pytest.mark.asyncio
async def test_create_event_for_format_success(mock_bot):
    """Test the create_event_for_format method when successful."""
    cog = Nominations(mock_bot)
    cog.next_wednesday = datetime.date(2023, 3, 15)  # A Wednesday

    # Create a proper mock channel
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_bot.get_channel.return_value = mock_channel

    # Mock the guild
    mock_guild = MagicMock(spec=discord.Guild)
    mock_channel.guild = mock_guild

    # Mock the create_scheduled_event method
    mock_event = MagicMock()
    mock_event.url = "https://discord.com/events/123456789"
    mock_guild.create_scheduled_event = AsyncMock(return_value=mock_event)

    # Use a string for the format name, not the built-in format function
    format_name = "Modern"

    # Call the create_event_for_format method
    await cog.create_event_for_format(format_name)

    # Verify create_scheduled_event was called
    mock_guild.create_scheduled_event.assert_called_once()

    # Verify the channel.send was called
    mock_channel.send.assert_called_once()

    # Verify the message contains the event URL and format name
    message = mock_channel.send.call_args[0][0]
    assert format_name in message
    assert mock_event.url in message


@pytest.mark.asyncio
async def test_create_event_for_format_forbidden(mock_bot):
    """Test the create_event_for_format method when forbidden."""
    cog = Nominations(mock_bot)
    cog.next_wednesday = datetime.date(2023, 3, 15)  # A Wednesday

    # Create a proper mock channel
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_bot.get_channel.return_value = mock_channel

    # Mock the guild
    mock_guild = MagicMock(spec=discord.Guild)
    mock_channel.guild = mock_guild

    # Mock the create_scheduled_event method to raise Forbidden
    # Fix the Forbidden error creation
    response = MagicMock()
    forbidden_error = discord.Forbidden(response, "Missing permissions")
    mock_guild.create_scheduled_event = AsyncMock(side_effect=forbidden_error)

    # Mock the send_error_message method
    mock_bot.send_error_message = AsyncMock()

    # Call the create_event_for_format method
    await cog.create_event_for_format(format)

    # Verify send_error_message was called
    mock_bot.send_error_message.assert_called_once()


@pytest.mark.asyncio
async def test_create_event_for_format_exception(mock_bot):
    """Test the create_event_for_format method when an exception occurs."""
    cog = Nominations(mock_bot)
    cog.next_wednesday = datetime.date(2023, 3, 15)  # A Wednesday

    # Create a proper mock channel
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_bot.get_channel.return_value = mock_channel

    # Mock the guild
    mock_guild = MagicMock(spec=discord.Guild)
    mock_channel.guild = mock_guild

    # Mock the create_scheduled_event method to raise an exception
    mock_guild.create_scheduled_event = AsyncMock(side_effect=Exception("Test error"))

    # Mock the send_error_message method
    mock_bot.send_error_message = AsyncMock()

    # Call the create_event_for_format method
    await cog.create_event_for_format(format)

    # Verify send_error_message was called
    mock_bot.send_error_message.assert_called_once()


@pytest.mark.asyncio
async def test_nominate_command_format_too_long(mock_bot, mock_interaction):
    """Test the nominate command when format is too long."""
    cog = Nominations(mock_bot)
    cog.can_nominate = True  # Allow nominations

    # Create a format that's too long (>55 characters)
    long_format = "A" * 56

    # Call the nominate method directly
    await cog.nominate.callback(cog, mock_interaction, long_format)

    # Verify the response was sent
    mock_interaction.response.send_message.assert_called_once()

    # Verify the message indicates the format is too long
    message = mock_interaction.response.send_message.call_args[0][0]
    assert "too long" in message
