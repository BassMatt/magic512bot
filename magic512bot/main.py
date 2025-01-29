import os

import config
import discord
from config import LOGGER
from database import SessionLocal, init_db
from discord.ext import commands


class Magic512Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    # Syncs guild commands to specified guild
    async def setup_hook(self):
        LOGGER.info("Starting setup_hook")

        init_db()
        self.db = SessionLocal

        # Other setup code...
        await self.load_cogs()
        await self.sync_commands()

    async def load_cogs(self):
        LOGGER.info("Loading cogs")
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    LOGGER.info(f"Loading extension: cogs.{filename[:-3]}")
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    LOGGER.info(f"Loaded cog: {filename[:-3]}")
                except Exception as e:
                    LOGGER.info(f"Failed to load cog {filename[:-3]}")
                    LOGGER.info(f"Error: {str(e)}")

    async def sync_commands(self):
        LOGGER.info("Syncing commands")
        # For syncing to a specific guild (faster for testing)
        test_guild = discord.Object(id=config.TEST_GUILD_ID)
        self.tree.copy_global_to(guild=test_guild)
        if config.TEST_GUILD_ID:
            LOGGER.info(f"{[cmd.name for cmd in self.tree.get_commands()]}")
            synced = await self.tree.sync(guild=test_guild)
            LOGGER.info(f"Synced commands to guild {config.TEST_GUILD_ID}")
            LOGGER.info(f"synced {len(synced)} commands to guild")
        else:
            # For syncing globally (can take up to an hour to propagate)
            await self.tree.sync()
            LOGGER.info("Synced commands globally")

    async def on_ready(self):
        LOGGER.info(f"{self.user} has connected!")


async def main():
    # Create bot instance
    bot = Magic512Bot()

    # Start the bot with your token
    async with bot:
        await bot.start(config.BOT_TOKEN)


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutting down... 👋")
