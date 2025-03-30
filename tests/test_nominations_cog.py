import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from typing import Any, cast
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import discord
import pytest
from discord import app_commands
from freezegun import freeze_time

from magic512bot.cogs.nomination import (
    MAX_USER_NOMINATIONS,
    MORNING_HOUR,
    Nomination,
    Weekday,
    is_nomination_period_active,
)
from tests.utils import track_tasks

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def nomination_cog(mock_bot: MagicMock) -> Nomination:
    """Create a Nomination cog with all background tasks disabled."""
    with patch("discord.ext.tasks.Loop.start"):
        cog = Nomination(mock_bot)
        mock_bot.wait_until_ready = AsyncMock()
        return cog


@pytest.fixture
def frozen_datetime() -> datetime:
    """Get the current frozen datetime."""
    return datetime.now()


@pytest.fixture
def mock_channel():
    """Create a mock discord channel."""
    channel = AsyncMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def mock_interaction():
    """Create a mock discord interaction."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = 12345
    interaction.user.display_name = "TestUser"
    return interaction


# Test scenarios for nomination periods
NOMINATION_PERIOD_SCENARIOS = [
    pytest.param("2024-03-14 09:00:00", True, id="thursday_9am_open"),
    pytest.param("2024-03-14 08:59:00", False, id="thursday_before_9am_closed"),
    pytest.param("2024-03-17 08:59:00", True, id="sunday_before_9am_open"),
    pytest.param("2024-03-17 09:00:00", False, id="sunday_9am_closed"),
]


@pytest.mark.parametrize("test_time,expected_active", NOMINATION_PERIOD_SCENARIOS)
def test_is_nomination_period_active(test_time: str, expected_active: bool) -> None:
    """Test if nominations are active during specific time periods."""
    with freeze_time(test_time):
        assert is_nomination_period_active() == expected_active


# Test scenarios for nomination commands
NOMINATION_COMMAND_SCENARIOS = [
    pytest.param(
        True,  # nominations_active
        [],  # existing_nominations
        "Modern",  # format_name
        True,  # should_succeed
        "Your nomination for **Modern**",  # expected_message
        id="success",
    ),
    pytest.param(
        False,  # nominations_active
        [],  # existing_nominations
        "Modern",  # format_name
        False,  # should_succeed
        "Nominations are currently closed",  # expected_message
        id="nominations_closed",
    ),
    pytest.param(
        True,  # nominations_active
        ["Format1", "Format2"],  # existing_nominations
        "Modern",  # format_name
        False,  # should_succeed
        "maximum of 2 nominations",  # expected_message
        id="max_nominations",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "nominations_active,existing_nominations,format_name,should_succeed,expected_message",
    NOMINATION_COMMAND_SCENARIOS,
)
async def test_nominate_command(
    nomination_cog: Nomination,
    mock_interaction: discord.Interaction,
    mock_channel: discord.TextChannel,
    nominations_active: bool,
    existing_nominations: list[str],
    format_name: str,
    should_succeed: bool,
    expected_message: str,
) -> None:
    """Test nomination command under various scenarios."""
    nomination_cog.bot.get_channel = MagicMock(return_value=mock_channel)

    with (
        patch(
            "magic512bot.cogs.nomination.is_nomination_period_active",
            return_value=nominations_active,
        ),
        patch(
            "magic512bot.cogs.nomination.get_user_nominations",
            return_value=existing_nominations,
        ),
        patch("magic512bot.cogs.nomination.add_nomination") as mock_add,
    ):
        await nomination_cog.nominate.callback(
            nomination_cog, mock_interaction, format_name
        )

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        message = mock_interaction.response.send_message.call_args[0][0]
        assert expected_message in message
        assert mock_interaction.response.send_message.call_args[1]["ephemeral"] is True

        # Verify nomination was added only on success
        if should_succeed:
            mock_add.assert_called_once()
            assert mock_add.call_args[1]["format"] == format_name
        else:
            mock_add.assert_not_called()


@pytest.mark.asyncio
async def test_nominate_command_error(
    nomination_cog: Nomination, mock_interaction: discord.Interaction
) -> None:
    """Test the nominate command when an error occurs."""
    cog = nomination_cog

    # Create a proper mock for the interaction
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.user = MagicMock(spec=discord.Member)
    mock_interaction.user.id = 12345

    with patch(
        "magic512bot.cogs.nomination.is_nomination_period_active", return_value=True
    ):
        with patch("magic512bot.cogs.nomination.get_user_nominations", return_value=[]):
            with patch(
                "magic512bot.cogs.nomination.add_nomination",
                side_effect=ValueError("Test error"),
            ):
                # Cast the command to the correct type and get its callback
                nominate_command = cast(app_commands.Command, cog.nominate)
                callback = cast(
                    Callable[[Any, discord.Interaction, str], Any],
                    nominate_command.callback,
                )
                await callback(cog, mock_interaction, "Modern")

                mock_interaction.response.send_message.assert_called_once()
                message = mock_interaction.response.send_message.call_args[0][0]
                assert "❌" in message
                assert "Test error" in message


@pytest.mark.asyncio
async def test_nominate_command_exception(
    nomination_cog: Nomination, mock_interaction: discord.Interaction
) -> None:
    """Test the nominate command when an unexpected exception occurs."""
    cog = nomination_cog

    # Create a proper mock for the interaction
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.user = MagicMock(spec=discord.Member)
    mock_interaction.user.id = 12345

    with patch(
        "magic512bot.cogs.nomination.is_nomination_period_active", return_value=True
    ):
        with patch("magic512bot.cogs.nomination.get_user_nominations", return_value=[]):
            with patch(
                "magic512bot.cogs.nomination.add_nomination",
                side_effect=Exception("Unexpected error"),
            ):
                # Cast the command to the correct type and get its callback
                nominate_command = cast(app_commands.Command, cog.nominate)
                callback = cast(
                    Callable[[Any, discord.Interaction, str], Any],
                    nominate_command.callback,
                )
                await callback(cog, mock_interaction, "Modern")

                mock_interaction.response.send_message.assert_called_once()
                message = mock_interaction.response.send_message.call_args[0][0]
                assert "❌" in message
                assert "error" in message.lower()


@pytest.mark.asyncio
async def test_nominate_command_format_too_long(
    nomination_cog: Nomination, mock_interaction: discord.Interaction
) -> None:
    """Test the nominate command when format is too long."""
    cog = nomination_cog

    # Create a proper mock for the interaction
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.user = MagicMock(spec=discord.Member)
    mock_interaction.user.id = 12345

    with patch(
        "magic512bot.cogs.nomination.is_nomination_period_active", return_value=True
    ):
        long_format = "A" * 56
        # Cast the command to the correct type and get its callback
        nominate_command = cast(app_commands.Command, cog.nominate)
        callback = cast(
            Callable[[Any, discord.Interaction, str], Any], nominate_command.callback
        )
        await callback(cog, mock_interaction, long_format)
        mock_interaction.response.send_message.assert_called_once()
        message = mock_interaction.response.send_message.call_args[0][0]
        assert "too long" in message


@pytest.mark.asyncio
async def test_nominate_command_success_with_channel_message(
    nomination_cog: Nomination,
    mock_interaction: discord.Interaction,
    mock_bot: MagicMock,
) -> None:
    """Test the nominate command sends a message to the channel after successful nomination."""
    cog = nomination_cog

    # Create a proper mock for the interaction
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.user = MagicMock(spec=discord.Member)
    mock_interaction.user.id = 12345
    mock_interaction.user.display_name = "TestUser"

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_bot.get_channel.return_value = mock_channel

    with patch(
        "magic512bot.cogs.nomination.is_nomination_period_active", return_value=True
    ):
        with patch("magic512bot.cogs.nomination.get_user_nominations", return_value=[]):
            with patch("magic512bot.cogs.nomination.add_nomination") as mock_add:
                # Cast the command to the correct type and get its callback
                nominate_command = cast(app_commands.Command, cog.nominate)
                callback = cast(
                    Callable[[Any, discord.Interaction, str], Any],
                    nominate_command.callback,
                )
                await callback(cog, mock_interaction, "Modern")

                mock_add.assert_called_once()
                assert mock_add.call_args[1]["user_id"] == mock_interaction.user.id
                assert mock_add.call_args[1]["format"] == "Modern"

                mock_interaction.response.send_message.assert_called_once()
                user_message = mock_interaction.response.send_message.call_args[0][0]
                assert "Your nomination for **Modern**" in user_message
                assert (
                    mock_interaction.response.send_message.call_args[1]["ephemeral"]
                    is True
                )

                mock_bot.get_channel.assert_called_once()
                mock_channel.send.assert_called_once()
                channel_message = mock_channel.send.call_args[0][0]
                assert "has nominated" in channel_message
                assert "Modern" in channel_message


@pytest.mark.asyncio
async def test_nominate_command_success_channel_not_found(
    nomination_cog: Nomination,
    mock_interaction: discord.Interaction,
    mock_bot: MagicMock,
) -> None:
    """Test the nominate command when the channel is not found."""
    cog = nomination_cog

    # Create a proper mock for the interaction
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.user = MagicMock(spec=discord.Member)
    mock_interaction.user.id = 12345

    mock_bot.get_channel.return_value = None

    with patch(
        "magic512bot.cogs.nomination.is_nomination_period_active", return_value=True
    ):
        with patch("magic512bot.cogs.nomination.get_user_nominations", return_value=[]):
            with patch("magic512bot.cogs.nomination.add_nomination") as mock_add:
                # Cast the command to the correct type and get its callback
                nominate_command = cast(app_commands.Command, cog.nominate)
                callback = cast(
                    Callable[[Any, discord.Interaction, str], Any],
                    nominate_command.callback,
                )
                await callback(cog, mock_interaction, "Modern")

                mock_add.assert_called_once()
                mock_interaction.response.send_message.assert_called_once()
                user_message = mock_interaction.response.send_message.call_args[0][0]
                assert "Your nomination for **Modern**" in user_message
                mock_bot.get_channel.assert_called_once()


@pytest.mark.asyncio
@freeze_time("2024-03-18 10:00:00")  # Monday 10 AM
async def test_check_missed_tasks_poll_monday(
    nomination_cog_with_mocks: dict[str, Any],
) -> None:
    """Test checking missed tasks on Monday."""
    logger.info("Starting test_check_missed_tasks_poll_monday")
    cog = nomination_cog_with_mocks["cog"]

    with (
        patch(
            "magic512bot.cogs.nomination.get_last_nomination_open_date",
            return_value=datetime.now().date() - timedelta(days=1),
        ),
    ):
        cog.create_poll = AsyncMock()
        await cog.check_missed_tasks()

        cog.create_poll.assert_called_once()


@pytest.mark.asyncio
@freeze_time("2024-03-16 10:00:00")  # Saturday 10 AM
async def test_check_missed_tasks_nominations_saturday(
    nomination_cog_with_mocks: dict[str, Any],
) -> None:
    """Test checking missed tasks on Saturday."""
    cog = nomination_cog_with_mocks["cog"]

    with (
        patch("discord.ext.tasks.Loop.start"),
        patch("discord.ext.tasks.Loop.before_loop"),
        patch("discord.ext.tasks.Loop.after_loop"),
        patch("magic512bot.cogs.nomination.tasks.datetime") as mock_tasks_dt,
        patch("magic512bot.cogs.nomination.get_last_run_date", return_value=None),
    ):
        mock_tasks_dt.now = MagicMock(return_value=datetime(2024, 3, 16, 10, 0))
        mock_tasks_dt.datetime = datetime

        cog.send_nominations_open_message = AsyncMock()
        await cog.check_missed_tasks()

        cog.send_nominations_open_message.assert_called_once()


@pytest.mark.asyncio
@freeze_time("2024-03-19 08:00:00")
async def test_check_missed_tasks_poll_tuesday_before_9am(
    nomination_cog_with_mocks: dict[str, Any],
) -> None:
    """Test checking missed tasks on Tuesday before 9 AM."""
    cog = nomination_cog_with_mocks["cog"]
    mock_session = nomination_cog_with_mocks["session"]

    logger.debug("Starting Tuesday before 9am test")
    current_date = datetime.now().date()
    logger.debug(f"Current frozen date: {current_date} (type: {type(current_date)})")

    # Mock the channel
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    cog.bot.get_channel = MagicMock(return_value=mock_channel)

    # Create a spy version of create_poll that will actually call through
    original_create_poll = cog.create_poll

    async def spy_create_poll():
        await original_create_poll()

    cog.create_poll = AsyncMock(side_effect=spy_create_poll)

    with (
        patch("magic512bot.cogs.nomination.get_poll_last_run_date", return_value=None),
        patch("magic512bot.cogs.nomination.set_poll") as mock_set_poll,
        patch(
            "magic512bot.cogs.nomination.get_all_nominations",
            return_value=[MagicMock(format="Modern")],
        ),
    ):
        await cog.check_missed_tasks()

        cog.create_poll.assert_called_once()
        mock_set_poll.assert_called_once_with(
            mock_session,
            mock_channel.id,
        )


# Test data for different scenarios
MISSED_TASK_SCENARIOS = [
    pytest.param(
        "2024-03-14 10:00:00",  # Thursday after 9 AM
        True,  # should_send_nominations
        False,  # should_create_poll
        "thursday_nominations",  # expected_task_name
        date(2024, 3, 14),  # expected_date
        id="thursday_after_9am",
    ),
    pytest.param(
        "2024-03-16 10:00:00",  # Saturday
        True,
        False,
        "thursday_nominations",
        date(2024, 3, 16),
        id="saturday",
    ),
    pytest.param(
        "2024-03-17 08:00:00",  # Sunday before 9 AM
        True,
        False,
        "thursday_nominations",
        date(2024, 3, 17),
        id="sunday_before_9am",
    ),
    pytest.param(
        "2024-03-17 10:00:00",  # Sunday after 9 AM
        False,
        True,
        "sunday_poll",
        date(2024, 3, 17),
        id="sunday_after_9am",
    ),
    pytest.param(
        "2024-03-20 10:00:00",  # Wednesday
        False,
        False,
        None,
        date(2024, 3, 20),
        id="outside_windows",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_time,should_send_nominations,should_create_poll,expected_task_name,expected_date",
    MISSED_TASK_SCENARIOS,
)
async def test_check_missed_tasks(
    mock_bot: MagicMock,
    test_time: str,
    should_send_nominations: bool,
    should_create_poll: bool,
    expected_task_name: str | None,
    expected_date: date,
) -> None:
    """Test check_missed_tasks behavior for different times."""
    with freeze_time(test_time):
        cog = Nomination(mock_bot)

        with patch.object(
            cog, "send_nominations_open_message", new_callable=AsyncMock
        ) as mock_send_nominations:
            with patch.object(
                cog, "create_poll", new_callable=AsyncMock
            ) as mock_create_poll:
                logger.debug(f"Test time: {test_time}")
                logger.debug(
                    f"Expected date: {expected_date} (type: {type(expected_date)})"
                )
                current_date = datetime.now().date()
                logger.debug(
                    f"Current frozen date: {current_date} (type: {type(current_date)})"
                )

                with (
                    patch(
                        "magic512bot.cogs.nomination.get_last_run_date",
                        return_value=None,
                    ),
                ):
                    await cog.check_missed_tasks()

                    # Check if nominations were sent
                    if should_send_nominations:
                        mock_send_nominations.assert_called_once()
                    else:
                        mock_send_nominations.assert_not_called()

                    # Check if poll was created
                    if should_create_poll:
                        mock_create_poll.assert_called_once()
                    else:
                        mock_create_poll.assert_not_called()


# Test data for daily checks
DAILY_CHECK_SCENARIOS = [
    pytest.param(
        "2024-03-14 09:00:00",  # Thursday 9 AM
        True,
        "thursday_nominations",
        id="thursday_9am",
    ),
    pytest.param(
        "2024-03-17 09:00:00",  # Sunday 9 AM
        True,
        "sunday_poll",
        id="sunday_9am",
    ),
    pytest.param(
        "2024-03-15 09:00:00",  # Friday 9 AM
        False,
        None,
        id="non_task_day",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_time,should_run_task,expected_task_name", DAILY_CHECK_SCENARIOS
)
async def test_daily_check(
    mock_bot: MagicMock,
    test_time: str,
    should_run_task: bool,
    expected_task_name: str | None,
) -> None:
    """Test daily_check behavior for different times."""
    with freeze_time(test_time):
        cog = Nomination(mock_bot)

        with patch.object(
            cog, "send_nominations_open_message", new_callable=AsyncMock
        ) as mock_send_nominations:
            with patch.object(
                cog, "create_poll", new_callable=AsyncMock
            ) as mock_create_poll:
                with (
                    patch(
                        "magic512bot.cogs.nomination.get_last_run_date",
                        return_value=None,
                    ),
                ):
                    await cog.daily_check()

                    if should_run_task:
                        if expected_task_name == "thursday_nominations":
                            mock_send_nominations.assert_called_once()
                            mock_create_poll.assert_not_called()
                        else:
                            mock_create_poll.assert_called_once()
                            mock_send_nominations.assert_not_called()
                    else:
                        mock_send_nominations.assert_not_called()
                        mock_create_poll.assert_not_called()


MISSED_TASKS_INDIVIDUAL_SCENARIOS = [
    pytest.param(
        "2024-03-17 08:00:00",  # Sunday before 9 AM
        "thursday_nominations",
        True,  # should_send_nominations
        False,  # should_create_poll
        id="sunday_before_9am",
    ),
    pytest.param(
        "2024-03-19 08:00:00",  # Tuesday before 9 AM
        "sunday_poll",
        False,  # should_send_nominations
        True,  # should_create_poll
        id="tuesday_before_9am",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_time,expected_task_name,should_send_nominations,should_create_poll",
    MISSED_TASKS_INDIVIDUAL_SCENARIOS,
)
async def test_check_missed_tasks_individual_scenarios(
    nomination_cog_with_mocks: dict[str, Any],
    test_time: str,
    expected_task_name: str,
    should_send_nominations: bool,
    should_create_poll: bool,
) -> None:
    """Test specific scenarios for check_missed_tasks."""
    with freeze_time(test_time):
        cog = nomination_cog_with_mocks["cog"]

        logger.debug(f"Testing scenario with time: {test_time}")
        current_date = datetime.now().date()
        logger.debug(
            f"Current frozen date: {current_date} (type: {type(current_date)})"
        )

        cog.send_nominations_open_message = AsyncMock()
        cog.create_poll = AsyncMock()

        with (
            patch("magic512bot.cogs.nomination.get_last_run_date", return_value=None),
        ):
            await cog.check_missed_tasks()

            if should_send_nominations:
                cog.send_nominations_open_message.assert_called_once()
            else:
                cog.send_nominations_open_message.assert_not_called()

            if should_create_poll:
                cog.create_poll.assert_called_once()
            else:
                cog.create_poll.assert_not_called()


@pytest.mark.asyncio
async def test_send_nominations_open_message_sets_last_run_date(
    nomination_cog: Nomination,
) -> None:
    """Test that send_nominations_open_message sets the last run date."""
    cog = nomination_cog
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    cog.bot = MagicMock()
    cog.bot.get_channel = MagicMock(return_value=mock_channel)

    with (
        patch("magic512bot.cogs.nomination.set_last_run_date") as mock_set_date,
    ):
        await cog.send_nominations_open_message()

        mock_channel.send.assert_called_once()
        mock_set_date.assert_called_once_with(
            cog.bot.db.begin().__enter__(),
            "thursday_nominations",
            datetime.now().date(),
        )


@pytest.mark.asyncio
async def test_create_poll_sets_last_run_date(
    nomination_cog: Nomination,
) -> None:
    """Test that create_poll sets the last run date."""
    cog = nomination_cog
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    cog.bot = MagicMock()
    cog.bot.get_channel = MagicMock(return_value=mock_channel)

    with (
        patch(
            "magic512bot.cogs.nomination.get_all_nominations",
            return_value=[MagicMock(format="Modern")],
        ),
        patch("magic512bot.cogs.nomination.set_last_run_date") as mock_set_date,
    ):
        await cog.create_poll()

        mock_channel.send.assert_called_once()
        mock_set_date.assert_called_once_with(
            cog.bot.db.begin().__enter__(),
            "sunday_poll",
            datetime.now().date(),
        )


@pytest.mark.asyncio
async def test_create_poll_no_nominations_does_not_set_last_run_date(
    nomination_cog: Nomination,
) -> None:
    """Test that create_poll does not set last run date when there are no nominations."""
    cog = nomination_cog
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    cog.bot = MagicMock()
    cog.bot.get_channel = MagicMock(return_value=mock_channel)

    with (
        patch("magic512bot.cogs.nomination.get_all_nominations", return_value=[]),
        patch("magic512bot.cogs.nomination.set_last_run_date") as mock_set_date,
    ):
        await cog.create_poll()

        mock_channel.send.assert_called_once()
        mock_set_date.assert_not_called()


@pytest.mark.asyncio
async def test_nomination_limit(
    nomination_cog: Nomination, mock_interaction: discord.Interaction
) -> None:
    """Test that users can add two nominations but not three, and verify database storage."""
    cog = nomination_cog

    # Setup mock interaction and channel as before...
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.user = MagicMock(spec=discord.Member)
    mock_interaction.user.id = 12345
    mock_interaction.user.display_name = "TestUser"

    # Setup mock channel for nomination announcements
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_channel.send.return_value = AsyncMock()

    # Add this line to make the bot return our mock channel
    cog.bot.get_channel = MagicMock(return_value=mock_channel)
    stored_nominations: list[str] = []

    def mock_add_nomination(**kwargs: Any) -> None:
        stored_nominations.append(kwargs["format"])

    with (
        patch(
            "magic512bot.cogs.nomination.is_nomination_period_active", return_value=True
        ),
        patch(
            "magic512bot.cogs.nomination.add_nomination",
            side_effect=mock_add_nomination,
        ),
        patch(
            "magic512bot.cogs.nomination.get_user_nominations",
            side_effect=lambda *args: stored_nominations,
        ),
    ):
        # Cast the command to the correct type and get its callback
        nominate_command = cast(app_commands.Command, cog.nominate)
        callback = cast(
            Callable[[Any, discord.Interaction, str], Any], nominate_command.callback
        )

        # First nomination should succeed
        await callback(cog, mock_interaction, "Modern")
        assert len(stored_nominations) == 1
        assert stored_nominations[0] == "Modern"
        assert (
            "Your nomination for **Modern**"
            in mock_interaction.response.send_message.call_args[0][0]
        )

        # Second nomination should succeed
        await callback(cog, mock_interaction, "Pioneer")
        assert len(stored_nominations) == 2
        assert "Pioneer" in stored_nominations
        assert (
            "Your nomination for **Pioneer**"
            in mock_interaction.response.send_message.call_args[0][0]
        )

        # Third nomination should fail
        await callback(cog, mock_interaction, "Legacy")
        assert len(stored_nominations) == 2  # Should still be 2
        assert "Legacy" not in stored_nominations
        assert (
            "maximum of 2 nominations"
            in mock_interaction.response.send_message.call_args[0][0]
        )

        # Verify channel messages were sent for successful nominations
        assert mock_channel.send.call_count == 2
        assert "Modern" in mock_channel.send.call_args_list[0][0][0]
        assert "Pioneer" in mock_channel.send.call_args_list[1][0][0]


@pytest.mark.asyncio
async def test_nominate_command_basic(nomination_cog: Nomination) -> None:
    """Test basic nomination command functionality."""
    # Setup
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.user = MagicMock(spec=discord.Member)
    mock_interaction.user.id = 12345
    mock_interaction.user.display_name = "TestUser"

    mock_channel = AsyncMock(spec=discord.TextChannel)
    nomination_cog.bot.get_channel = MagicMock(return_value=mock_channel)

    # Test
    with (
        patch(
            "magic512bot.cogs.nomination.is_nomination_period_active", return_value=True
        ),
        patch("magic512bot.cogs.nomination.get_user_nominations", return_value=[]),
        patch("magic512bot.cogs.nomination.add_nomination") as mock_add,
    ):
        await nomination_cog.nominate(mock_interaction, "Modern")

        # Verify user response
        mock_interaction.response.send_message.assert_called_once()
        response = mock_interaction.response.send_message.call_args[0][0]
        assert "Your nomination for **Modern**" in response
        assert mock_interaction.response.send_message.call_args[1]["ephemeral"] is True

        # Verify nomination was added
        mock_add.assert_called_once_with(session=ANY, user_id=12345, format="Modern")


@pytest.mark.asyncio
async def test_send_nominations_open_message(nomination_cog: Nomination) -> None:
    """Test sending the nominations open message."""
    # Setup
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    nomination_cog.bot.get_channel = MagicMock(return_value=mock_channel)

    # Test
    with patch("magic512bot.cogs.nomination.set_nomination") as mock_set:
        await nomination_cog.send_nominations_open_message()

        # Verify message was sent
        mock_channel.send.assert_called_once()

        # Verify nomination was recorded
        mock_set.assert_called_once()


@pytest.mark.asyncio
async def test_create_poll_with_nominations(nomination_cog: Nomination) -> None:
    """Test creating a poll when nominations exist."""
    # Setup
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    nomination_cog.bot.get_channel = MagicMock(return_value=mock_channel)

    test_nominations = [MagicMock(format="Modern"), MagicMock(format="Pioneer")]

    # Test
    with (
        patch(
            "magic512bot.cogs.nomination.get_all_nominations",
            return_value=test_nominations,
        ),
        patch("magic512bot.cogs.nomination.clear_all_nominations") as mock_clear,
        patch("magic512bot.cogs.nomination.set_poll") as mock_set_poll,
    ):
        await nomination_cog.create_poll()

        # Verify poll was created
        mock_channel.send.assert_called_once()

        # Verify nominations were cleared and poll was recorded
        mock_clear.assert_called_once()
        mock_set_poll.assert_called_once()


@pytest.mark.asyncio
async def test_create_poll_no_nominations(nomination_cog: Nomination) -> None:
    """Test creating a poll when no nominations exist."""
    # Setup
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    nomination_cog.bot.get_channel = MagicMock(return_value=mock_channel)

    # Test
    with (
        patch("magic512bot.cogs.nomination.get_all_nominations", return_value=[]),
        patch("magic512bot.cogs.nomination.set_poll") as mock_set_poll,
    ):
        await nomination_cog.create_poll()

        # Verify message was sent
        mock_channel.send.assert_called_once()

        # Verify no poll was recorded
        mock_set_poll.assert_not_called()


@pytest.mark.asyncio
async def test_check_missed_tasks_basic(nomination_cog: Nomination) -> None:
    """Test basic missed tasks checking functionality."""
    # Setup
    with (
        freeze_time("2024-03-14 10:00:00"),  # Thursday after 9 AM
        patch(
            "magic512bot.cogs.nomination.get_last_nomination_open_date",
            return_value=None,
        ),
        patch.object(
            nomination_cog, "have_sent_nominations_open_message", return_value=False
        ),
        patch.object(nomination_cog, "send_nominations_open_message") as mock_send,
    ):
        # Test
        await nomination_cog.check_missed_tasks()

        # Verify nominations message was sent
        mock_send.assert_called_once()
