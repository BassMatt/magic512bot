import discord
from discord import app_commands
from discord.ext  import commands
import os
import config
from database import init_db
import asyncio

intents = discord.Intents.default()
intents.message_content = True
class Magic512Bot(commands.Bot):
    def __init__(self):
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    # Syncs guild commands to specified guild
    async def setup_hook(self):
        await init_db()
        await self.load_cogs()
        await self.sync_commands()

    async def load_cogs(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'Loaded cog: {filename[:-3]}')
                except Exception as e:
                    print(f'Failed to load cog {filename[:-3]}')
                    print(f'Error: {str(e)}')

    async def sync_commands(self):
        # For syncing to a specific guild (faster for testing)
        if config.TEST_GUILD_ID:
            guild = discord.Object(id=config.TEST_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced commands to guild {config.TEST_GUILD_ID}")
        else:
            # For syncing globally (can take up to an hour to propagate)
            await self.tree.sync()
            print("Synced commands globally")

bot = Magic512Bot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("Bot is ready!")

asyncio.run(bot.start(config.BOT_TOKEN))