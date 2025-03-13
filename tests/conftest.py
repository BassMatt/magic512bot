import os
import sys
from unittest.mock import AsyncMock, MagicMock

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


@pytest.fixture
def engine() -> Engine:
    """Create an in-memory SQLite database for testing."""
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def tables(engine) -> None:
    """Create all tables in the test database."""
    register_models()
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine, tables) -> Session:
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


@pytest_asyncio.fixture
async def mock_bot():
    """Create a mock bot instance for testing."""
    bot = MagicMock()
    bot.db = MagicMock()
    session_mock = MagicMock()
    context_manager_mock = MagicMock()
    context_manager_mock.__enter__ = MagicMock(return_value=session_mock)
    context_manager_mock.__exit__ = MagicMock(return_value=None)
    bot.db.begin = MagicMock(return_value=context_manager_mock)
    return bot


@pytest_asyncio.fixture
async def mock_interaction() -> discord.Interaction:
    """Create a mock Discord interaction for testing."""
    interaction = MagicMock()
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.send_modal = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    # Create a proper Member mock for the user
    user = MagicMock(spec=discord.Member)
    user.id = 12345
    user.display_name = "TestUser"
    user.mention = "<@12345>"
    user.roles = []
    user.remove_roles = AsyncMock()
    user.add_roles = AsyncMock()

    interaction.user = user

    # Create a guild mock
    guild = MagicMock(spec=discord.Guild)
    guild.roles = []
    interaction.guild = guild

    return interaction


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
