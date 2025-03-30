from datetime import date, datetime, time, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from magic512bot.config import LOGGER, TIMEZONE
from magic512bot.main import Magic512Bot
from magic512bot.services.nomination import (
    MAX_NOMINATION_LENGTH,
    add_nomination,
    clear_all_nominations,
    get_all_nominations,
    get_user_nominations,
)
from magic512bot.services.task_run import (
    get_active_poll_id,
    get_last_nomination_open_date,
    get_poll_last_run_date,
    set_nomination,
    set_poll,
)

from .constants import Channels, Weekday

# Define the timezone at the top of the file
MAX_USER_NOMINATIONS = 2
MORNING_HOUR = time(hour=9, minute=0, tzinfo=TIMEZONE)


def is_nomination_period_active() -> bool:
    """
    Check if the nomination period is currently active.
    Nominations are open from Thursday 9:00 AM to Sunday 9:00 AM.
    """
    now = datetime.now(TIMEZONE)
    current_day = now.weekday()
    current_hour = now.hour

    if (
        (current_day == Weekday.THURSDAY.value and current_hour >= MORNING_HOUR.hour)
        or current_day in [Weekday.FRIDAY.value, Weekday.SATURDAY.value]
        or (current_day == Weekday.SUNDAY.value and current_hour < MORNING_HOUR.hour)
    ):
        return True
    return False


class Nomination(commands.Cog):
    def __init__(self, bot: Magic512Bot):
        self.bot: Magic512Bot = bot
        LOGGER.info("Nominations Cog Initialized")
        # Start the daily check
        self.daily_check.start()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Handle missed tasks once the bot is fully ready."""
        try:
            LOGGER.info("Nomination Cog: Checking for missed tasks...")
            await self.check_missed_tasks()
            LOGGER.info("Nomination Cog: Finished checking for missed tasks")
        except Exception as e:
            LOGGER.error(f"Error checking missed tasks: {e!s}")

    async def cog_unload(self) -> None:
        """Cancel the daily check when the cog is unloaded."""
        self.daily_check.cancel()
        self.check_poll_status.cancel()

    @app_commands.command(name="nominate", description="Nominate a format to play next")
    @app_commands.describe(format="The format you want to nominate")
    async def nominate(self, interaction: discord.Interaction, format: str) -> None:
        """Nominate a format to play next."""
        # Explicitly cast interaction.user to Member
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Failed to fetch your member information!", ephemeral=True
            )
            return

        # Check if nominations are currently open
        if not is_nomination_period_active():
            await interaction.response.send_message(
                "Nominations are currently closed. "
                "Nominations are open from Sunday 9:00 AM to Tuesday 9:00 AM.",
                ephemeral=True,
            )
            return

        if len(format) > MAX_NOMINATION_LENGTH:
            await interaction.response.send_message(
                "Format is too long. Please keep it under 55 characters.",
                ephemeral=True,
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
                # Send a message to the user
                await interaction.response.send_message(
                    f"✅ Your nomination for **{format}** has been recorded!",
                    ephemeral=True,
                )

                # Also send a message to the wc-wednesday channel
                channel = self.bot.get_channel(Channels.WC_WEDNESDAY_CHANNEL_ID)
                if channel and isinstance(channel, discord.TextChannel):
                    await channel.send(
                        f"🎲 **{interaction.user.display_name}** has nominated "
                        f"**{format}**!"
                    )
                else:
                    LOGGER.error(
                        f"Could not find text channel with ID "
                        f"{Channels.WC_WEDNESDAY_CHANNEL_ID}"
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

    async def have_sent_nominations_open_message(self) -> bool:
        """Check if we have sent the nominations open message for the current week."""
        last_nominations_open = None
        with self.bot.db.begin() as session:
            last_nominations_open = get_last_nomination_open_date(session)
        if not last_nominations_open:
            return False

        now = datetime.now(TIMEZONE)
        today = now.date()
        current_time = now.time()

        # Find this week's Thursday date
        days_until_thursday = (3 - today.weekday()) % 7  # 3 is Thursday
        this_thursday = today + timedelta(days=days_until_thursday)

        # If today is after Thursday or today is Thursday and time is after 9am,
        # then we're in the valid period for sending
        in_nominations_period = (today > this_thursday) or (
            today == this_thursday and current_time >= time(9, 0, tzinfo=TIMEZONE)
        )

        # Find next Sunday date
        days_until_sunday = (6 - today.weekday()) % 7  # 6 is Sunday
        this_sunday = today + timedelta(days=days_until_sunday)

        # If today is before Sunday or today is Sunday and time is before 9am,
        # then we're still in the valid period
        in_nominations_period = in_nominations_period and (
            (today < this_sunday)
            or (today == this_sunday and current_time < time(9, 0, tzinfo=TIMEZONE))
        )

        # If we're not in the nomination period, return False immediately
        if not in_nominations_period:
            return False

        # Calculate this week's Wednesday (the start of our week)
        # Wednesday is 2 in weekday()
        days_since_wednesday = (today.weekday() - 2) % 7
        this_wednesday = today - timedelta(days=days_since_wednesday)

        # Check if the last run was this week (on or after Wednesday)
        return last_nominations_open >= this_wednesday

    async def have_created_poll(self) -> bool:
        """
        Check if we've already created a poll for this week.

        Returns:
            bool: True if a poll has been created for this week, False otherwise.
        """
        with self.bot.db.begin() as session:
            # Get the active poll ID and last poll creation date
            last_poll_creation = get_poll_last_run_date(session)

            # If there's no last poll creation date, we haven't created a poll
            if last_poll_creation is None:
                return False

            # Calculate this week's Wednesday (the start of our week)
            today = datetime.now(TIMEZONE).date()
            # Wednesday is 2 in weekday()
            days_since_wednesday = (today.weekday() - 2) % 7
            this_wednesday = today - timedelta(days=days_since_wednesday)

            # Check if the last poll creation was this week (on or after Wednesday)
            return last_poll_creation >= this_wednesday

    async def check_missed_tasks(self) -> None:
        """
        Check if any tasks were missed while the bot was down.

        Windows for missed tasks:
        - Nominations: Thursday 9AM -> Sunday 9AM
        - Poll Creation: Sunday 9AM -> Tuesday 9AM
        """
        now = datetime.now(TIMEZONE)
        LOGGER.info(
            f"Checking missed tasks at {now}\n"
            f"    (weekday: {now.weekday()}, hour: {now.hour})"
        )

        # Check for missed nomination opening (Sunday 9:00 AM - Tuesday 9:00 AM)
        if not await self.have_sent_nominations_open_message():
            LOGGER.info("Running missed nominations open task")
            await self.send_nominations_open_message()

        if not await self.have_created_poll():
            LOGGER.info("Running missed poll creation task")
            await self.create_poll()

    @tasks.loop(time=MORNING_HOUR)
    async def daily_check(self) -> None:
        """Check if we need to run weekly tasks today."""
        now = datetime.now(TIMEZONE)
        today = now.date()

        with self.bot.db.begin() as session:
            last_nominations_open = get_last_nomination_open_date(session)
            last_poll_creation = get_poll_last_run_date(session)

            # Thursday - Open nominations, if we haven't run it today
            if (
                now.weekday() == Weekday.THURSDAY.value
                and last_nominations_open != today
            ):
                await self.send_nominations_open_message()
                LOGGER.info(f"Ran Nominations Open Task on {today} during Daily Check")

            # Sunday - Create poll, if we haven't run it today
            elif now.weekday() == Weekday.SUNDAY.value and last_poll_creation != today:
                await self.create_poll()
                LOGGER.info(f"Ran Poll Creation Task on {today} during Daily Check")

    async def send_nominations_open_message(self) -> None:
        """Send a message to open nominations."""
        channel = self.bot.get_channel(Channels.WC_WEDNESDAY_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            LOGGER.error(
                f"Could not find channel with ID {Channels.WC_WEDNESDAY_CHANNEL_ID}"
            )
            return

        try:
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

            # Only update last run date if message was sent successfully
            with self.bot.db.begin() as session:
                set_nomination(session)

        except Exception as e:
            LOGGER.error(f"Error sending nominations open message: {e}")
            raise

    def get_next_wednesday(self) -> date:
        """Calculate the date of next Wednesday.

        Returns:
            datetime.date: The date of the next Wednesday.
        """
        today = datetime.now(TIMEZONE).date()
        days_until_wednesday = (2 - today.weekday()) % 7  # 2 represents Wednesday
        return today + timedelta(days=days_until_wednesday)

    async def create_poll(self) -> None:
        LOGGER.info("Attempting to create poll...")
        channel = self.bot.get_channel(Channels.WC_WEDNESDAY_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            LOGGER.error(
                f"Could not find channel with ID {Channels.WC_WEDNESDAY_CHANNEL_ID}"
            )
            return

        try:
            with self.bot.db.begin() as session:
                LOGGER.info("Fetching nominations from database...")
                nominations = get_all_nominations(session)
                unique_formats = set(nom.format.title() for nom in nominations)
                LOGGER.info(
                    f"Found {len(unique_formats)} unique formats: {unique_formats}"
                )

                if not unique_formats:
                    LOGGER.info(
                        "No nominations were submitted this week skipping poll creation"
                    )
                    await channel.send("No nominations were submitted this week :(")
                    return

                # Use the helper method
                next_wednesday = self.get_next_wednesday()
                formatted_date = next_wednesday.strftime("%B %d, %Y")
                poll_title = f"WC Wednesday Format Voting for {formatted_date}"

                # Create the poll
                poll = discord.Poll(
                    question=poll_title,
                    duration=timedelta(hours=12),
                    multiple=True,
                )

                for format_name in unique_formats:
                    poll.add_answer(text=f"{format_name}")

                # Send the poll
                poll_message = await channel.send(
                    content="# 🗳️ Format Voting 🗳️\n\nVote for next week's format!",
                    poll=poll,
                )

                # Store the poll ID and clear nominations
                clear_all_nominations(session)
                LOGGER.info(f"Created poll with {len(unique_formats)} format options")
                set_poll(session, poll_message.id)

            LOGGER.info("Successfully created poll")

        except Exception as e:
            LOGGER.error(f"Error creating poll: {e}", exc_info=True)
            raise

    async def create_wc_wednesday_event(self, format: str) -> None:
        """Create a Discord event for the winning format."""
        LOGGER.info(f"Creating event for format: {format}")

        channel = self.bot.get_channel(Channels.WC_WEDNESDAY_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            LOGGER.error("Could not find WC Wednesday channel")
            return

        try:
            # Use the helper method
            next_wednesday = self.get_next_wednesday()

            # Check if event already exists
            existing_events = await channel.guild.fetch_scheduled_events()
            for event in existing_events:
                if (
                    event.name.startswith("WC Wednesday:")
                    and event.start_time.date() == next_wednesday
                ):
                    LOGGER.info("Event already exists for next Wednesday")
                    return

            # Cube takes 30 more minutes because draft
            is_cube_format = "cube" in format.lower()
            start_hour = 18 if is_cube_format else 19
            start_minute = 30 if is_cube_format else 0

            start_time = datetime.combine(
                next_wednesday,
                time(hour=start_hour, minute=start_minute, tzinfo=TIMEZONE),
            )
            end_time = start_time + timedelta(hours=2)

            # Create the event
            event = await channel.guild.create_scheduled_event(
                name=f"WC Wednesday: {format}",
                description=(
                    f"This week's WC Wednesday we're playing **{format}**!\n\n"
                    f"Come join us at Pat's Games :)"
                ),
                start_time=start_time,
                end_time=end_time,
                location="Pat's Games",
                privacy_level=discord.PrivacyLevel.guild_only,
            )

            await channel.send(
                f"# 📅 Event Created! 📅\n\n"
                f"The winning format is **{format}**!\n\n"
                f"An event has been scheduled for Wednesday at 7:00 PM. "
                f"Click here to RSVP: {event.url}"
            )

        except Exception as e:
            LOGGER.error(f"Error creating event: {e}", exc_info=True)
            await self.bot.send_error_message(
                "There was an error creating the event. Please create it manually."
            )

    def in_poll_checking_window(self) -> bool:
        """
        Check if we're in the poll checking window (Sunday 9PM to Tuesday 9AM).

        Polls are normally created at 9:00 AM Sunday, so we start checking at
        9:00 PM Sunday, and Monday/Tuesday to handle delayed polls.
        """
        now = datetime.now(TIMEZONE)
        current_weekday = now.weekday()
        current_time = now.time()
        evening_time = time(hour=21, minute=0, tzinfo=TIMEZONE)

        # Sunday after 9PM
        if current_weekday == Weekday.SUNDAY.value and current_time >= evening_time:
            return True

        # All day Monday
        if current_weekday == Weekday.MONDAY.value:
            return True

        # Tuesday before 9AM
        if current_weekday == Weekday.TUESDAY.value and current_time < MORNING_HOUR:
            return True

        return False

    @tasks.loop(minutes=5)
    async def check_poll_status(self) -> None:
        """Periodically check if active poll has ended."""
        # Only run during poll window
        if not self.in_poll_checking_window():
            return

        if await self.have_created_poll():
            return

        with self.bot.db.begin() as session:
            active_poll_id = get_active_poll_id(session)
            if not active_poll_id:
                LOGGER.warning("No active poll ID found")
                return

            LOGGER.debug(f"Checking status of active poll: {active_poll_id}")
            try:
                channel = self.bot.get_channel(Channels.WC_WEDNESDAY_CHANNEL_ID)
                if not isinstance(channel, discord.TextChannel):
                    LOGGER.warning("Could not find WC Wednesday channel")
                    return

                message = await channel.fetch_message(active_poll_id)
                if not hasattr(message, "poll") or not message.poll:
                    LOGGER.warning("Active poll message does not have a poll")
                    return

                if message.poll.is_finalised():
                    LOGGER.info("Found ended poll, processing results")
                    if not (victor_answer := message.poll.victor_answer):
                        LOGGER.warning("No victor answer found for poll")
                        return

                    await self.create_wc_wednesday_event(format=str(victor_answer))

            except discord.NotFound:
                LOGGER.warning(f"Active poll message {active_poll_id} not found")
            except Exception as e:
                LOGGER.error(f"Error checking poll status: {e}", exc_info=True)


async def setup(bot: Magic512Bot) -> None:
    """Load the Nomination cog."""
    await bot.add_cog(Nomination(bot))
