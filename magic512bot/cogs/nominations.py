import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from magic512bot.config import LOGGER, WC_WEDNESDAY_CHANNEL_ID
from magic512bot.main import Magic512Bot
from magic512bot.services.nominations import (
    add_nomination,
    clear_all_nominations,
    get_all_nominations,
    get_user_nominations,
)

THURSDAY = 3
SUNDAY = 6
MAX_USER_NOMINATIONS = 2


class Nominations(commands.Cog):
    def __init__(self, bot: Magic512Bot):
        self.bot: Magic512Bot = bot
        LOGGER.info("Nominations Cog Initialized")
        # Track the last run dates to ensure we only run once per day
        self.last_thursday_run = None
        self.last_sunday_run = None
        self.can_nominate = False
        # Store the active poll ID
        self.active_poll_id = None
        # Start the daily check
        self.daily_check.start()

    def cog_unload(self):
        self.daily_check.cancel()

    @app_commands.command(name="nominate", description="Nominate a format to play next")
    @app_commands.describe(format="The format you want to nominate")
    async def nominate(self, interaction: discord.Interaction, format: str):
        """Nominate a format to play next."""
        # Explicitly cast interaction.user to Member
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Failed to fetch your member information!", ephemeral=True
            )
            return

        if not self.can_nominate:
            await interaction.response.send_message(
                "Nominations are not currently open.", ephemeral=True
            )
            return

        # Check if user already has 2 nominations
        with self.bot.db.begin() as session:
            if (
                len(get_user_nominations(session, interaction.user.id))
                >= MAX_USER_NOMINATIONS
            ):
                await interaction.response.send_message(
                    "You have already used your maximum of 2 nominations this week.",
                    ephemeral=True,
                )
                return

        with self.bot.db.begin() as session:
            try:
                add_nomination(
                    session=session, user_id=interaction.user.id, format=format
                )
                await interaction.response.send_message(
                    f"✅ Your nomination for **{format}** has been recorded!",
                    ephemeral=True,
                )
            except ValueError as e:
                await interaction.response.send_message(
                    f"❌ {e!s}",
                    ephemeral=True,
                )
            except Exception as e:
                LOGGER.error(f"Error in nominate command: {e!s}")
                await interaction.response.send_message(
                    "❌ Error recording nomination. Try again later.",
                    ephemeral=True,
                )

    @tasks.loop(time=datetime.time(hour=9, minute=0))  # Run at 9:00 AM every day
    async def daily_check(self):
        """Check if we need to run weekly tasks today."""
        now = datetime.datetime.now()
        today = now.date()

        # Thursday - Open nominations
        if now.weekday() == THURSDAY and self.last_thursday_run != today:
            await self.open_nominations()
            self.last_thursday_run = today
            LOGGER.info(f"Ran Thursday task on {today}")

        # Sunday - Create poll
        elif now.weekday() == SUNDAY and self.last_sunday_run != today:
            await self.create_poll()
            self.last_sunday_run = today
            LOGGER.info(f"Ran Sunday task on {today}")

    @daily_check.before_loop
    async def before_daily_check(self):
        """Wait until the bot is ready before starting the scheduler."""
        await self.bot.wait_until_ready()

    async def open_nominations(self):
        """Send a message to open nominations."""
        channel = self.bot.get_channel(WC_WEDNESDAY_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            LOGGER.error(f"Could not find channel with ID {WC_WEDNESDAY_CHANNEL_ID}")
            return

        embed = discord.Embed(
            title="🎮 Format Nominations Open! 🎮",
            description=(
                "Nominate formats for next week's WC Wednesday!\n\n"
                "Use `/nominate format=format_name` to submit your nomination.\n"
                "Nominations will close on Sunday at 9:00 AM when voting begins."
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="You can have up to 2 nominations.")

        await channel.send(embed=embed)
        LOGGER.info("Sent nominations open message")

        self.can_nominate = True

    async def create_poll(self):
        """Create a poll with all nominations."""
        channel = self.bot.get_channel(WC_WEDNESDAY_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            LOGGER.error(f"Could not find channel with ID {WC_WEDNESDAY_CHANNEL_ID}")
            return

        with self.bot.db.begin() as session:
            unique_formats = set(
                nom.format.title() for nom in get_all_nominations(session)
            )

            if not unique_formats:
                await channel.send("No nominations were submitted this week.")
                return

            # Calculate the date of the next Wednesday
            today = datetime.datetime.now().date()
            days_until_wednesday = (2 - today.weekday()) % 7  # 2 represents Wednesday
            next_wednesday = today + datetime.timedelta(days=days_until_wednesday)
            formatted_date = next_wednesday.strftime("%B %d, %Y")

            poll_title = f"WC Wednesday Format Voting for {formatted_date}"

            # Create the poll
            poll = discord.Poll(
                question=poll_title,
                duration=datetime.timedelta(days=1),
                multiple=True,
            )

            for format_name in unique_formats:
                poll.add_answer(text=f"**{format_name}**")

            # Send the poll
            poll_message = await channel.send(
                content="# 🗳️ Format Voting 🗳️\n\nVote for next week's format!", poll=poll
            )

            # Store the poll ID for later reference
            self.active_poll_id = poll_message.id

            # Store the next Wednesday date for event creation
            self.next_wednesday = next_wednesday

            # Store the format options for later reference
            self.format_options = list(unique_formats)

            # Clear nominations after creating poll
            clear_all_nominations(session)
            self.can_nominate = False  # Close Nominations (until next thursday)
            LOGGER.info(f"Created poll with {len(unique_formats)} format options")

    @commands.Cog.listener()
    async def on_poll_end(self, poll: discord.Poll):
        """Handle poll end event."""
        # Check if this poll is from a message we're tracking
        if (
            not hasattr(poll, "message")
            or not poll.message
            or poll.message.id != self.active_poll_id
        ):
            return

        LOGGER.info("Format voting poll has ended. Processing results...")

        # Find the winning format
        if not poll.victor_answer:
            await self.bot.send_error_message("No victor answer found in poll")
            return

        winning_format = poll.victor_answer.text

        await self.create_event_for_format(winning_format)

        # Reset the active poll ID
        self.active_poll_id = None

    async def create_event_for_format(self, format_name: str):
        """Create a Discord event for the winning format."""
        # Get the channel's guild
        channel = self.bot.get_channel(WC_WEDNESDAY_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            LOGGER.error(f"Could not find channel with ID {WC_WEDNESDAY_CHANNEL_ID}")
            return

        guild = channel.guild

        # Calculate event time (next Wednesday at 7:00 PM)
        event_time = datetime.datetime.combine(
            self.next_wednesday,
            datetime.time(hour=19, minute=0),  # 7:00 PM
        )

        # Event end time (2 hours later)
        event_end_time = event_time + datetime.timedelta(hours=2)

        try:
            # Create the event
            event = await guild.create_scheduled_event(
                name=f"WC Wednesday: {format_name}",
                description=(
                    f"This week's WC Wednesday we're playing **{format_name}**!\n\n"
                ),
                start_time=event_time,
                end_time=event_end_time,
                location="Pat's Games",  # Use the channel name as location
                privacy_level=discord.PrivacyLevel.guild_only,
            )

            # Announce the event creation
            await channel.send(
                f"# 📅 Event Created! 📅\n\n"
                f"The winning format is **{format_name}**!\n\n"
                f"An event has been scheduled for Wednesday at 7:00 PM. "
                f"Click here to RSVP: {event.url}"
            )

            LOGGER.info(f"Created event for format {format_name}")

        except discord.Forbidden as e:
            LOGGER.error(f"Bot does not have permission to create events: {e}")
            await self.bot.send_error_message(
                "I tried to create an event, but I don't have permission. "
                "Please create the event manually."
            )
        except Exception as e:
            LOGGER.error(f"Error creating event: {e}")
            await self.bot.send_error_message(
                "There was an error creating the event. Please create it manually."
            )


async def setup(bot: Magic512Bot) -> None:
    await bot.add_cog(Nominations(bot))
