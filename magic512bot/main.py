import discord
from discord.ext  import commands
import os
import config
from config import logger
from database import init_db, get_db
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
intents = discord.Intents.default()
intents.message_content = True
class Magic512Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.db_session: AsyncSession | None = None

    # Syncs guild commands to specified guild
    async def setup_hook(self):
        try:
            await init_db(timeout_seconds=5)
            logger.info("Starting setup_hook")
            # Other setup code...
            logger.info(f"Type of get_db(): {type(get_db())}")
            db_gen = get_db()
            logger.info(f"Type of db_gen: {type(db_gen)}")
            self.db_session = await anext(db_gen)
            logger.info(f"Type of self.db_session after await anext(): {type(self.db_session)}")
            assert isinstance(self.db_session, AsyncSession), f"self.db_session is of type {type(self.db_session)}, expected AsyncSession"
        except asyncio.TimeoutError:
            logger.info("Database initialization timed out")
        await self.load_cogs()
        await self.sync_commands()

    async def load_cogs(self):
        logger.info("Loading cogs")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:

                    logger.info(f'Loading extension: cogs.{filename[:-3]}')
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f'Loaded cog: {filename[:-3]}')
                except Exception as e:
                    logger.info(f'Failed to load cog {filename[:-3]}')
                    logger.info(f'Error: {str(e)}')

    async def sync_commands(self):
        logger.info("Syncing commands")
        # For syncing to a specific guild (faster for testing)
        test_guild = discord.Object(id=config.TEST_GUILD_ID)
        self.tree.copy_global_to(guild=test_guild)
        if config.TEST_GUILD_ID:
            logger.info(f"{[cmd.name for cmd in self.tree.get_commands()]}")
            synced = await self.tree.sync(guild=test_guild)
            logger.info(f"Synced commands to guild {config.TEST_GUILD_ID}")
            logger.info(f"synced {len(synced)} commands to guild")
        else:
            # For syncing globally (can take up to an hour to propagate)
            await self.tree.sync()
            logger.info("Synced commands globally")

    async def close(self):
        if self.db_session:
            await self.db_session.close()
        await super().close()
    
    async def on_ready(self):
        logger.info(f"{self.user} has connected!")

bot = Magic512Bot()

logger.info("Running bot!")
try:
    asyncio.run(bot.start(config.BOT_TOKEN))
except Exception as e:
    logger.info(e)