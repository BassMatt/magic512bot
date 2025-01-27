from dotenv import load_dotenv
import os

load_dotenv()

TEST_GUILD_ID = 1074039539280121936

DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")
BOT_TOKEN = os.getenv("BOT_TOKEN")