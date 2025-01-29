import sys
import asyncio
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent.absolute()

# Add the project root and the magic512bot directory to the Python path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "magic512bot"))

from unittest.mock import patch
from magic512bot.main import Magic512Bot
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

print(f"Python path: {sys.path}")  # This will print the Python path for debugging

@pytest.fixture
async def bot():
    """
    Fixture to create and setup a bot instance for testing.
    """
    with patch('discord.Client.login'):
        test_bot = Magic512Bot()
        
        # Setup the bot
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, asyncio.run, test_bot.setup_hook())
        
        yield test_bot
        
        # Cleanup
        await loop.run_in_executor(None, asyncio.run, test_bot.close())

@pytest.fixture
async def db_session(bot) -> AsyncSession:
    """
    Fixture to provide a database session.
    """
    if isinstance(bot.db_session, AsyncSession):
        return bot.db_session
    else:
        print("UNEXPECTED TYPE")
        raise TypeError("Unexpected type for bot.db")