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


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("magic512bot")
    logger.setLevel(logging.INFO)  # Set this to the desired level

    # Create handlers
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = logging.FileHandler("bot.log")
    c_handler.setLevel(logging.INFO)  # Console handler level
    f_handler.setLevel(logging.DEBUG)  # File handler level

    # Create formatters and add it to handlers
    format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    c_handler.setFormatter(format)
    f_handler.setFormatter(format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger


LOGGER: Final[logging.Logger] = setup_logger()
