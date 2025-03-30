import asyncio
import logging
import os
import sys
from collections.abc import Generator
from datetime import datetime, time, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
import pytest_asyncio
from sqlalchemy.orm import Session

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock environment variables before importing any app modules
os.environ["DB_CONNECTION_STRING"] = "sqlite:///:memory:"
os.environ["BOT_TOKEN"] = "test_token"

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from magic512bot.models import register_models
from magic512bot.models.base import Base

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@pytest.fixture
def engine() -> Engine:
    """Create an in-memory SQLite database for testing."""
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def tables(engine: Engine) -> Generator[None]:
    """Create all tables in the test database."""
    register_models()
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine: Engine, tables: None) -> Generator[Session]:
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    # Only rollback if the transaction is still active
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest_asyncio.fixture(scope="function")
async def mock_bot() -> MagicMock:
    """Create a simple mock bot."""
    bot = MagicMock()
    bot.wait_until_ready = AsyncMock()
    return bot


class GuildMock(MagicMock):
    """Custom mock class for Discord Guild."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._roles: list[discord.Role] = []
        self._members: list[discord.Member] = []
        self.get_role = MagicMock()
        self.get_channel = MagicMock()

    def set_roles(self, roles: list[discord.Role]) -> None:
        """Set the roles list."""
        self._roles = roles

    def set_members(self, members: list[discord.Member]) -> None:
        """Set the members list."""
        self._members = members

    @property
    def roles(self) -> list[discord.Role]:
        """Get the roles list."""
        return self._roles

    @property
    def members(self) -> list[discord.Member]:
        """Get the members list."""
        return self._members


class InteractionMock(MagicMock):
    """Custom mock class for Discord Interaction."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._guild = GuildMock(spec=discord.Guild)

        # Mock the response
        response = MagicMock()
        response.send_message = AsyncMock()
        response.send_modal = AsyncMock()
        self.response = response

        # Mock the followup
        followup = MagicMock()
        followup.send = AsyncMock()
        self.followup = followup

        # Create a proper Member mock for the user
        user = MagicMock(spec=discord.Member)
        user.id = 12345
        user.display_name = "TestUser"
        user.mention = "<@12345>"
        user.roles = []
        user.remove_roles = AsyncMock()
        user.add_roles = AsyncMock()
        self.user = user

    @property
    def guild(self) -> discord.Guild:
        """Get the guild instance."""
        return self._guild


@pytest_asyncio.fixture
async def mock_interaction() -> discord.Interaction:
    """Create a mock Discord interaction for testing."""
    return InteractionMock()


@pytest_asyncio.fixture
async def mock_member() -> discord.Member:
    """Create a mock Discord member for testing."""
    member = MagicMock(spec=discord.Member)
    member.id = 67890
    member.display_name = "TestMember"
    member.mention = "<@67890>"
    member.roles = []
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    member.send = AsyncMock()
    return member


@pytest.fixture
def mock_datetime() -> Generator[datetime]:
    """Base fixture for datetime mocking."""
    logger.info("Setting up mock_datetime fixture")
    mock_now = datetime(2024, 3, 18, 10, 0)  # Monday 10 AM

    # Only patch where datetime is actually imported
    with (
        patch("magic512bot.cogs.nomination.datetime") as mock_dt,
        patch("datetime.datetime") as mock_global_dt,
    ):
        logger.info("Configuring datetime mocks")
        for dt_mock in [mock_dt, mock_global_dt]:
            dt_mock.now = MagicMock(return_value=mock_now)
            dt_mock.datetime = datetime
            dt_mock.time = time
            dt_mock.timedelta = timedelta
            dt_mock.date = datetime.date
            dt_mock.combine = datetime.combine

        logger.info("mock_datetime fixture setup complete")
        yield mock_now


@pytest.fixture
def mock_thursday_datetime() -> Generator[datetime]:
    """Thursday-specific datetime mock."""
    mock_now = datetime(2024, 3, 14, 9, 0)  # Thursday 9 AM
    with (
        patch("magic512bot.cogs.nomination.datetime") as mock_dt,
        patch("magic512bot.services.task_run.datetime") as mock_service_dt,
        patch("datetime.datetime") as mock_global_dt,
    ):
        for dt_mock in [mock_dt, mock_service_dt, mock_global_dt]:
            dt_mock.now = MagicMock(return_value=mock_now)
            dt_mock.datetime = datetime
            dt_mock.time = time
            dt_mock.timedelta = timedelta

        yield mock_now


@pytest_asyncio.fixture
async def nomination_cog_with_mocks(mock_bot: MagicMock) -> dict[str, Any]:
    """Create a nomination cog with mocks."""
    from magic512bot.cogs.nomination import Nomination

    # Disable task loops
    with (
        patch("discord.ext.tasks.Loop.start"),
        patch("discord.ext.tasks.Loop.before_loop"),
        patch("discord.ext.tasks.Loop.after_loop"),
        patch("discord.ext.tasks.Loop.cancel"),
        patch("discord.ext.tasks.Loop.stop"),
    ):
        cog = Nomination(mock_bot)
        return {"cog": cog, "session": mock_bot.db.begin().__enter__()}


def setup_task_debugging() -> None:
    """Set up task debugging for tests."""

    def task_factory(loop: asyncio.AbstractEventLoop, coro: Any) -> asyncio.Task:
        task = asyncio.Task(coro, loop=loop)
        logger.debug(f"Created task: {task.get_name()}")

        def done_callback(task: asyncio.Task) -> None:
            try:
                task.result()
            except Exception as e:
                logger.error(f"Task {task.get_name()} failed: {e}")

        task.add_done_callback(done_callback)
        return task

    loop = asyncio.get_event_loop()
    loop.set_task_factory(task_factory)


# Add to pytest_configure
def pytest_configure(config: pytest.Config) -> None:
    setup_task_debugging()
