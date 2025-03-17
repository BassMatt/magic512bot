import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
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
    with (
        patch("discord.ext.tasks.Loop.start"),
        patch("discord.ext.tasks.Loop.before_loop"),
        patch("discord.ext.tasks.Loop.after_loop"),
    ):
        cog = Nomination(mock_bot)
        mock_bot.wait_until_ready = AsyncMock()
        return cog


@pytest.fixture
def frozen_datetime() -> datetime:
    """Get the current frozen datetime."""
    return datetime.now()


NOMINATION_COMMAND_SCENARIOS = [
    pytest.param(
        True,  # nominations_active
        [],  # existing_nominations
        "Modern",  # format_name
        None,  # expected_error
        True,  # should_succeed
        "Your nomination for **Modern**",  # expected_message
        id="success",
    ),
    pytest.param(
        False,  # nominations_active
        [],  # existing_nominations
        "Modern",  # format_name
        "Nominations are currently closed",  # expected_error
        False,  # should_succeed
        "Nominations are currently closed",  # expected_message
        id="nominations_closed",
    ),
    pytest.param(
        True,  # nominations_active
        [MagicMock(), MagicMock()],  # existing_nominations (MAX_USER_NOMINATIONS)
        "Modern",  # format_name
        "maximum of 2 nominations",  # expected_error
        False,  # should_succeed
        "maximum of 2 nominations",  # expected_message
        id="max_nominations",
    ),
    pytest.param(
        True,  # nominations_active
        [],  # existing_nominations
        "A" * 56,  # format_name (too long)
        "too long",  # expected_error
        False,  # should_succeed
        "too long",  # expected_message
        id="format_too_long",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "nominations_active,existing_nominations,format_name,expected_error,should_succeed,expected_message",
    NOMINATION_COMMAND_SCENARIOS,
)
async def test_nominate_command_scenarios(
    nomination_cog: Nomination,
    mock_interaction: discord.Interaction,
    nominations_active: bool,
    existing_nominations: list[MagicMock],
    format_name: str,
    expected_error: str | None,
    should_succeed: bool,
    expected_message: str,
) -> None:
    """Test various nomination command scenarios."""
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
            return_value=nominations_active,
        ),
        patch(
            "magic512bot.cogs.nomination.get_user_nominations",
            return_value=existing_nominations,
        ),
        patch("magic512bot.cogs.nomination.add_nomination") as mock_add,
        patch.object(cog.bot, "get_channel", return_value=None),
    ):
        # Cast the command to the correct type and get its callback
        nominate_command = cast(app_commands.Command, cog.nominate)
        callback = cast(
            Callable[[Any, discord.Interaction, str], Any], nominate_command.callback
        )
        await callback(cog, mock_interaction, format_name)

        # Verify the response
        mock_interaction.response.send_message.assert_called_once()
        message = mock_interaction.response.send_message.call_args[0][0]
        assert expected_message in message
        assert mock_interaction.response.send_message.call_args[1]["ephemeral"] is True

        # Verify add_nomination was called only on success
        if should_succeed:
            mock_add.assert_called_once()
            assert mock_add.call_args[1]["user_id"] == mock_interaction.user.id
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
    mock_session = nomination_cog_with_mocks["session"]

    with (
        patch(
            "magic512bot.cogs.nomination.get_last_run_date",
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
    mock_session = nomination_cog_with_mocks["session"]

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
        patch("magic512bot.cogs.nomination.get_last_run_date", return_value=None),
        patch("magic512bot.cogs.nomination.set_last_run_date") as mock_set_date,
        patch(
            "magic512bot.cogs.nomination.get_all_nominations",
            return_value=[MagicMock(format="Modern")],
        ),
    ):
        await cog.check_missed_tasks()

        cog.create_poll.assert_called_once()
        mock_set_date.assert_called_once_with(
            mock_session,
            "sunday_poll",
            current_date,  # This will be set by create_poll
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
                    f"Current date: {current_date} (type: {type(current_date)})"
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
        mock_session = nomination_cog_with_mocks["session"]

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
