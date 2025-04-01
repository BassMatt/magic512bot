import logging
import os
import sys
from typing import Final
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TEST_GUILD_ID = 1074039539280121936
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING") or ""
BOT_TOKEN = os.getenv("BOT_TOKEN") or ""
TIMEZONE = ZoneInfo("America/Chicago")  # This handles CDT/CST automatically
MODERATOR_CHANNEL_ID = 1074040269642661910


def is_running_tests() -> bool:
    """Check if code is being run by pytest."""
    return "pytest" in sys.modules


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("magic512bot")
    # Set DEBUG level for tests, INFO for normal running
    logger.setLevel(logging.DEBUG if is_running_tests() else logging.INFO)

    # Create handlers
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = logging.FileHandler("bot.log")

    # Console shows DEBUG for tests, INFO for normal running
    c_handler.setLevel(logging.DEBUG if is_running_tests() else logging.INFO)
    f_handler.setLevel(logging.DEBUG)  # File always logs DEBUG

    # Create formatters and add it to handlers
    format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    c_handler.setFormatter(format)
    f_handler.setFormatter(format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger


LOGGER: Final[logging.Logger] = setup_logger()
