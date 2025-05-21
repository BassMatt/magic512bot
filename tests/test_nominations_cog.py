import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import app_commands
from freezegun import freeze_time

from magic512bot.cogs.nomination import (
    Nomination,
    is_nomination_period_active,
)
from magic512bot.config import TIMEZONE

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
def mock_channel() -> AsyncMock:
    """Create a mock discord channel."""
    channel = AsyncMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def mock_interaction() -> MagicMock:
    """Create a mock discord interaction."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = 12345
    interaction.user.display_name = "TestUser"
    return interaction


def create_test_datetime(date_str: str, hour: int, minute: int = 0) -> str:
    """Create a datetime string in UTC based on Central Time."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    local_time = dt.replace(hour=hour, minute=minute, tzinfo=TIMEZONE)
    utc_time = local_time.astimezone(UTC)
    return utc_time.strftime("%Y-%m-%d %H:%M:%S")


# Test scenarios for nomination periods
NOMINATION_PERIOD_SCENARIOS = [
    pytest.param(
        create_test_datetime("2024-03-14", 9, 0), True, id="thursday_9am_open"
    ),
    pytest.param(
        create_test_datetime("2024-03-14", 8, 59),
        False,
        id="thursday_before_9am_closed",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 8, 59), True, id="sunday_before_9am_open"
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 9, 0), False, id="sunday_9am_closed"
    ),
    pytest.param(
        create_test_datetime("2024-03-14", 8, 59),
        False,
        id="thursday_just_before_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-14", 9, 1),
        True,
        id="thursday_just_after_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 8, 59),
        True,
        id="sunday_just_before_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 9, 1),
        False,
        id="sunday_just_after_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-14", 8, 59),
        False,
        id="thursday_minute_before_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-14", 9, 1),
        True,
        id="thursday_minute_after_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 8, 59),
        True,
        id="sunday_minute_before_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 9, 1),
        False,
        id="sunday_minute_after_9am",
    ),
]


@pytest.mark.parametrize("test_time,expected_active", NOMINATION_PERIOD_SCENARIOS)
def test_is_nomination_period_active(test_time: str, expected_active: bool) -> None:
    """Test if nominations are active during specific time periods."""
    with freeze_time(test_time):
        assert is_nomination_period_active() == expected_active


# Test scenarios for nomination commands
NOMINATION_COMMAND_SCENARIOS = [
    pytest.param(
        True,  # nominations_active: bool
        [],  # existing_nominations: list[str]
        "Modern",  # format_name: str
        True,  # should_succeed: bool
        "Your nomination for **Modern**",  # expected_message: str
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
    mock_interaction: MagicMock,
    mock_channel: AsyncMock,
    nominations_active: bool,
    existing_nominations: list[str],
    format_name: str,
    should_succeed: bool,
    expected_message: str,
) -> None:
    """Test nomination command under various scenarios."""
    with patch.object(nomination_cog.bot, "get_channel", return_value=mock_channel):
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
            patch(
                "magic512bot.cogs.nomination.should_run_nominations_this_week",
                return_value=True,
            ),
        ):
            nominate_command = cast(
                app_commands.Command[Any, Any, Any], nomination_cog.nominate
            )
            callback = cast(
                Callable[[Any, MagicMock, str], Awaitable[None]],
                nominate_command.callback,
            )
            await callback(nomination_cog, mock_interaction, format_name)

            # Verify response
            mock_interaction.response.send_message.assert_called_once()
            message = mock_interaction.response.send_message.call_args[0][0]
            assert expected_message in message
            assert (
                mock_interaction.response.send_message.call_args[1]["ephemeral"] is True
            )

            # Verify nomination was added only on success
            if should_succeed:
                mock_add.assert_called_once()
                assert mock_add.call_args[1]["format"] == format_name
            else:
                mock_add.assert_not_called()


@pytest.mark.asyncio
async def test_nominate_command_error(
    nomination_cog: Nomination,
    mock_interaction: MagicMock,
) -> None:
    """Test the nominate command when an error occurs."""
    cog = nomination_cog

    with (
        patch(
            "magic512bot.cogs.nomination.is_nomination_period_active",
            return_value=True,
        ),
        patch("magic512bot.cogs.nomination.get_user_nominations", return_value=[]),
        patch(
            "magic512bot.cogs.nomination.add_nomination",
            side_effect=ValueError("Test error"),
        ),
        patch(
            "magic512bot.cogs.nomination.should_run_nominations_this_week",
            return_value=True,
        ),
    ):
        # Cast the command to the correct type and get its callback
        nominate_command = cast(app_commands.Command[Any, Any, Any], cog.nominate)
        callback = cast(
            Callable[[Any, MagicMock, str], Awaitable[None]],
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

    with (
        patch(
            "magic512bot.cogs.nomination.is_nomination_period_active",
            return_value=True,
        ),
        patch("magic512bot.cogs.nomination.get_user_nominations", return_value=[]),
        patch(
            "magic512bot.cogs.nomination.add_nomination",
            side_effect=Exception("Unexpected error"),
        ),
        patch(
            "magic512bot.cogs.nomination.should_run_nominations_this_week",
            return_value=True,
        ),
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

    with (
        patch(
            "magic512bot.cogs.nomination.is_nomination_period_active",
            return_value=True,
        ),
        patch(
            "magic512bot.cogs.nomination.should_run_nominations_this_week",
            return_value=True,
        ),
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

    with (
        patch(
            "magic512bot.cogs.nomination.is_nomination_period_active", return_value=True
        ),
        patch("magic512bot.cogs.nomination.get_user_nominations", return_value=[]),
        patch("magic512bot.cogs.nomination.add_nomination") as mock_add,
        patch(
            "magic512bot.cogs.nomination.should_run_nominations_this_week",
            return_value=True,
        ),
    ):
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
        assert mock_interaction.response.send_message.call_args[1]["ephemeral"] is True

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

    with (
        patch(
            "magic512bot.cogs.nomination.is_nomination_period_active", return_value=True
        ),
        patch("magic512bot.cogs.nomination.get_user_nominations", return_value=[]),
        patch("magic512bot.cogs.nomination.add_nomination") as mock_add,
        patch(
            "magic512bot.cogs.nomination.should_run_nominations_this_week",
            return_value=True,
        ),
    ):
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
@freeze_time(create_test_datetime("2024-03-16", 10, 0))  # Saturday 10 AM CT
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
        patch(
            "magic512bot.cogs.nomination.get_last_nomination_open_date",
            return_value=None,
        ),
        patch(
            "magic512bot.cogs.nomination.should_run_nominations_this_week",
            return_value=True,
        ),
    ):
        mock_tasks_dt.now = MagicMock(return_value=datetime(2024, 3, 16, 10, 0))
        mock_tasks_dt.datetime = datetime

        cog.send_nominations_open_message = AsyncMock()
        await cog.check_missed_tasks()

        cog.send_nominations_open_message.assert_called_once()


# Test data for different scenarios
MISSED_TASK_SCENARIOS: list[Any] = [
    pytest.param(
        create_test_datetime("2024-03-14", 10, 0),
        True,  # should_send_nominations
        False,  # should_create_poll
        "thursday_nominations",
        date(2024, 3, 14),
        None,  # last_nomination_date
        None,  # last_poll_date
        id="thursday_after_9am_no_previous_runs",
    ),
    pytest.param(
        create_test_datetime("2024-03-16", 10, 0),
        True,
        False,
        "thursday_nominations",
        date(2024, 3, 16),
        None,  # last_nomination_date
        None,  # last_poll_date
        id="saturday_no_previous_runs",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 8, 0),
        True,
        False,
        "thursday_nominations",
        date(2024, 3, 17),
        None,  # last_nomination_date
        None,  # last_poll_date
        id="sunday_before_9am_no_previous_runs",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 10, 0),
        False,
        True,
        "sunday_poll",
        date(2024, 3, 17),
        None,  # last_nomination_date
        None,  # last_poll_date
        id="sunday_after_9am_no_previous_runs",
    ),
    pytest.param(
        create_test_datetime("2024-03-18", 10, 0),
        False,
        True,
        "sunday_poll",
        date(2024, 3, 18),
        None,  # last_nomination_date
        None,  # last_poll_date
        id="monday_after_9am_no_previous_runs",
    ),
    pytest.param(
        create_test_datetime("2024-03-20", 10, 0),
        False,
        False,
        None,
        date(2024, 3, 20),
        None,  # last_nomination_date
        None,  # last_poll_date
        id="outside_windows_no_previous_runs",
    ),
    # Cases where poll has already been run
    pytest.param(
        create_test_datetime("2024-03-17", 10, 0),
        False,
        False,
        "sunday_poll",
        date(2024, 3, 17),
        None,  # last_nomination_date
        date(2024, 3, 17),  # last_poll_date
        id="sunday_after_9am_poll_already_run",
    ),
    pytest.param(
        create_test_datetime("2024-03-18", 10, 0),
        False,
        False,
        "sunday_poll",
        date(2024, 3, 18),
        None,  # last_nomination_date
        date(2024, 3, 17),  # last_poll_date
        id="monday_after_9am_poll_already_run",
    ),
    # Cases where nominations have already been sent
    pytest.param(
        create_test_datetime("2024-03-14", 10, 0),
        False,
        False,
        "thursday_nominations",
        date(2024, 3, 14),
        date(2024, 3, 14),  # last_nomination_date
        None,  # last_poll_date
        id="thursday_after_9am_nominations_already_sent",
    ),
    pytest.param(
        create_test_datetime("2024-03-16", 10, 0),
        False,
        False,
        "thursday_nominations",
        date(2024, 3, 16),
        date(2024, 3, 14),  # last_nomination_date
        None,  # last_poll_date
        id="saturday_nominations_already_sent",
    ),
    pytest.param(
        create_test_datetime("2024-03-14", 9, 30),
        True,  # should_send_nominations
        False,  # should_create_poll
        "thursday_nominations",
        date(2024, 3, 14),
        date(2024, 3, 7),  # last week's nomination
        None,
        id="thursday_after_9am_last_week_nomination",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 9, 30),
        False,
        True,
        "sunday_poll",
        date(2024, 3, 17),
        date(2024, 3, 14),  # this week's nomination
        date(2024, 3, 10),  # last week's poll
        id="sunday_after_9am_last_week_poll",
    ),
    pytest.param(
        create_test_datetime("2024-03-14", 9, 1),
        True,
        False,
        "thursday_nominations",
        date(2024, 3, 14),
        None,
        None,
        id="thursday_just_after_9am_first_run",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_time,should_send_nominations,should_create_poll,expected_task_name,expected_date,last_nomination_date,last_poll_date",
    MISSED_TASK_SCENARIOS,
)
async def test_check_missed_tasks(
    mock_bot: MagicMock,
    test_time: str,
    should_send_nominations: bool,
    should_create_poll: bool,
    expected_task_name: str | None,
    expected_date: date,
    last_nomination_date: date | None,
    last_poll_date: date | None,
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
                        "magic512bot.cogs.nomination.get_last_nomination_open_date",
                        return_value=last_nomination_date,
                    ),
                    patch(
                        "magic512bot.cogs.nomination.get_poll_last_run_date",
                        return_value=last_poll_date,
                    ),
                    patch(
                        "magic512bot.cogs.nomination.should_run_nominations_this_week",
                        return_value=True,
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
        create_test_datetime("2024-03-14", 9, 0),
        True,
        "thursday_nominations",
        id="thursday",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 9, 0),
        True,
        "sunday_poll",
        id="sunday",
    ),
    pytest.param(
        create_test_datetime("2024-03-15", 9, 0),
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

        with (
            patch.object(
                cog, "send_nominations_open_message", new_callable=AsyncMock
            ) as mock_send_nominations,
            patch.object(
                cog, "create_poll", new_callable=AsyncMock
            ) as mock_create_poll,
            # Return None for last run date to simulate no previous runs
            patch(
                "magic512bot.cogs.nomination.get_poll_last_run_date",
                return_value=None,
            ),
            patch(
                "magic512bot.cogs.nomination.get_last_nomination_open_date",
                return_value=None,
            ),
            patch(
                "magic512bot.cogs.nomination.should_run_nominations_this_week",
                return_value=True,
            ),
        ):
            await cog.daily_check()

            if should_run_task:
                if expected_task_name == "thursday_nominations":
                    mock_send_nominations.assert_called_once()
                    mock_create_poll.assert_not_called()
                else:  # sunday_poll
                    mock_create_poll.assert_called_once()
                    mock_send_nominations.assert_not_called()
            else:
                mock_send_nominations.assert_not_called()
                mock_create_poll.assert_not_called()


MISSED_TASKS_INDIVIDUAL_SCENARIOS = [
    pytest.param(
        create_test_datetime("2024-03-17", 8, 0),
        "thursday_nominations",
        True,  # should_send_nominations
        False,  # should_create_poll
        id="sunday_before_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-19", 8, 0),
        "sunday_poll",
        False,  # should_send_nominations
        True,  # should_create_poll
        id="tuesday_before_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-14", 9, 1),
        "thursday_nominations",
        True,
        False,
        id="thursday_just_after_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-17", 9, 1),
        "sunday_poll",
        False,
        True,
        id="sunday_just_after_9am",
    ),
    pytest.param(
        create_test_datetime("2024-03-19", 8, 59),
        "sunday_poll",
        False,
        True,
        id="tuesday_just_before_9am",
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

        # Create mocks for the task methods
        cog.send_nominations_open_message = AsyncMock()
        cog.create_poll = AsyncMock()

        with (
            # Return None for both dates to simulate no previous runs
            patch(
                "magic512bot.cogs.nomination.get_last_nomination_open_date",
                return_value=None,
            ),
            patch(
                "magic512bot.cogs.nomination.get_poll_last_run_date",
                return_value=None,
            ),
            patch(
                "magic512bot.cogs.nomination.should_run_nominations_this_week",
                return_value=True,
            ),
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
    mock_message = MagicMock()
    mock_channel.send = AsyncMock(return_value=mock_message)

    # Create a mock session that will be returned by the context manager
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_session)
    mock_context.__exit__ = MagicMock(return_value=None)

    # Make the bot's db.begin() return our mock context
    with patch.object(cog.bot.db, "begin", return_value=mock_context):
        with (
            patch.object(cog.bot, "get_channel", return_value=mock_channel),
            patch("magic512bot.cogs.nomination.set_nomination") as mock_set_nomination,
        ):
            await cog.send_nominations_open_message()

            mock_channel.send.assert_called_once()
            mock_set_nomination.assert_called_once_with(mock_session)


@pytest.mark.asyncio
async def test_create_poll_sets_last_run_date(nomination_cog: Nomination) -> None:
    """Test that create_poll sets the last run date."""
    cog = nomination_cog
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = MagicMock()
    mock_message.id = 12345
    mock_message.poll = MagicMock(spec=discord.Poll)
    mock_channel.send = AsyncMock(return_value=mock_message)

    # Create a mock session that will be returned by the context manager
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_session)
    mock_context.__exit__ = MagicMock(return_value=None)

    # Make the bot's db.begin() return our mock context
    with patch.object(cog.bot.db, "begin", return_value=mock_context):
        with (
            patch.object(cog.bot, "get_channel", return_value=mock_channel),
            patch(
                "magic512bot.cogs.nomination.get_all_nominations",
                return_value=[MagicMock(format="Modern")],
            ),
            patch("magic512bot.cogs.nomination.set_poll") as mock_set_poll,
        ):
            await cog.create_poll()

            mock_channel.send.assert_called_once()
            mock_set_poll.assert_called_once_with(
                mock_session,
                mock_message.id,
            )


@pytest.mark.asyncio
async def test_check_missed_tasks_basic(nomination_cog: Nomination) -> None:
    """Test basic missed tasks checking functionality."""
    with (
        freeze_time(create_test_datetime("2024-03-14", 9, 0)),  # Thursday 9 AM CT
        patch(
            "magic512bot.services.task_run.get_last_nomination_open_date",
            return_value=None,
        ),
        patch.object(
            nomination_cog, "have_sent_nominations_open_message", return_value=False
        ),
        patch.object(nomination_cog, "send_nominations_open_message") as mock_send,
        patch(
            "magic512bot.cogs.nomination.should_run_nominations_this_week",
            return_value=True,
        ),
    ):
        # Create a mock session that will be returned by the context manager
        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_session)
        mock_context.__exit__ = MagicMock(return_value=None)

        # Make the bot's db.begin() return our mock context
        with patch.object(nomination_cog.bot.db, "begin", return_value=mock_context):
            await nomination_cog.check_missed_tasks()
            mock_send.assert_called_once()


@pytest.fixture
def nomination_cog_with_mocks() -> dict[str, Any]:
    """Create a Nomination cog with all necessary mocks."""
    mock_bot = MagicMock()
    mock_session = MagicMock()
    mock_bot.db.begin.return_value.__enter__.return_value = mock_session

    with patch("discord.ext.tasks.Loop.start"):
        cog = Nomination(mock_bot)
        mock_bot.wait_until_ready = AsyncMock()

    return {"cog": cog, "session": mock_session, "bot": mock_bot}


@pytest.mark.asyncio
async def test_nominate_command_not_nomination_week(
    nomination_cog: Nomination,
    mock_interaction: MagicMock,
) -> None:
    """Test nomination command when it's not a nomination week."""
    with patch(
        "magic512bot.cogs.nomination.should_run_nominations_this_week",
        return_value=False,
    ):
        nominate_command = cast(
            app_commands.Command[Any, Any, Any], nomination_cog.nominate
        )
        callback = cast(
            Callable[[Any, MagicMock, str], Awaitable[None]],
            nominate_command.callback,
        )
        await callback(nomination_cog, mock_interaction, "Modern")

        mock_interaction.response.send_message.assert_called_once()
        message = mock_interaction.response.send_message.call_args[0][0]
        assert "Nominations are not open this week" in message
        assert mock_interaction.response.send_message.call_args[1]["ephemeral"] is True
