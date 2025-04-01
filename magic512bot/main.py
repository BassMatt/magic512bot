import discord
from discord.ext import commands

from magic512bot.config import BOT_TOKEN, LOGGER, TEST_GUILD_ID
from magic512bot.database import SessionLocal, init_db


class Magic512Bot(commands.Bot):
    def __init__(self, command_prefix: str, intents: discord.Intents) -> None:
        super().__init__(command_prefix=command_prefix, intents=intents)

    # Syncs guild commands to specified guild
    async def setup_hook(self) -> None:
        LOGGER.info("Starting setup_hook")

        init_db()
        self.db = SessionLocal

        # Other setup code...
        await self.load_cogs()
        await self.sync_commands()

    async def load_cogs(self) -> None:
        LOGGER.info("Loading cogs")
        cog_modules = ["cogs.card_lender", "cogs.role_request", "cogs.nomination"]

        for module in cog_modules:
            try:
                LOGGER.info(f"Loading extension: {module}")
                await self.load_extension(f"magic512bot.{module}")
                LOGGER.info(f"Loaded cog: {module}")
            except (commands.ExtensionError, Exception) as e:
                LOGGER.error(f"Failed to load cog {module}")
                LOGGER.error(f"Error: {e!s}")

    async def sync_commands(self) -> None:
        LOGGER.info("Syncing commands")
        # For syncing to a specific guild (faster for testing)
        test_guild = discord.Object(id=TEST_GUILD_ID)
        self.tree.copy_global_to(guild=test_guild)
        if TEST_GUILD_ID:
            LOGGER.info(f"{[cmd.name for cmd in self.tree.get_commands()]}")
            synced = await self.tree.sync(guild=test_guild)
            LOGGER.info(f"Synced commands to guild {TEST_GUILD_ID}")
            LOGGER.info(f"synced {len(synced)} commands to guild")
        else:
            # For syncing globally (can take up to an hour to propagate)
            await self.tree.sync()
            LOGGER.info("Synced commands globally")

    async def on_ready(self) -> None:
        LOGGER.info(f"{self.user} has connected!")

        # Add diagnostic logging for intents and member caching
        LOGGER.info(f"Bot intents enabled: {self.intents}")
        LOGGER.info(f"Member intent enabled: {self.intents.members}")

        # Log guild member information
        for guild in self.guilds:
            LOGGER.info(f"Guild {guild.name} (ID: {guild.id}):")
            LOGGER.info(f"  Total member count: {guild.member_count}")
            LOGGER.info(f"  Cached member count: {len(guild.members)}")
            LOGGER.info(f"  Bot's top role: {guild.me.top_role}")

    async def send_error_message(self, error_message: str) -> bool:
        """
        Sends an error message to the moderator channel.

        Parameters
        ----------
        error_message : str
            The error message to send

        Returns
        -------
        bool
            True if the message was sent successfully, False otherwise
        """
        import discord

        from magic512bot.config import LOGGER, MODERATOR_CHANNEL_ID

        try:
            channel = self.get_channel(MODERATOR_CHANNEL_ID)
            if not channel or not isinstance(channel, discord.TextChannel):
                LOGGER.error(
                    f"Could not find moderator channel with ID {MODERATOR_CHANNEL_ID}"
                )
                return False

            # Create an embed for better formatting
            embed = discord.Embed(
                title="Error Report",
                description=error_message,
                color=discord.Color.red(),
            )
            embed.set_footer(
                text=f"Reported at \
                    {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )

            # Use bot.loop to schedule the message sending
            self.loop.create_task(channel.send(embed=embed))
            LOGGER.info(f"Error message sent to moderator channel: {error_message}")
            return True
        except Exception as e:
            LOGGER.error(f"Failed to send error to moderator channel: {e}")
            return False


async def main() -> None:
    # Create bot instance
    intents = discord.Intents.none()  # Start with no intents
    intents.guilds = True  # Needed for basic guild/channel operations
    intents.guild_messages = True  # Needed to fetch messages
    intents.guild_scheduled_events = True  # Needed to create events
    intents.members = True  # Needed to fetch members

    bot = Magic512Bot(command_prefix="!", intents=intents)

    # Start the bot with your token
    async with bot:
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutting down... 👋")
