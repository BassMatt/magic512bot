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
    should_run_nominations_this_week,
)

from .constants import Channels, Roles, Weekday

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

    return (
        (current_day == Weekday.THURSDAY.value and current_hour >= MORNING_HOUR.hour)
        or current_day in [Weekday.FRIDAY.value, Weekday.SATURDAY.value]
        or (current_day == Weekday.SUNDAY.value and current_hour < MORNING_HOUR.hour)
    )


def is_poll_creation_period_active() -> bool:
    """
    Check if the poll creation period is currently active.
    Polls are created from Sunday 9:00 AM to Tuesday 9:00 AM.
    """
    now = datetime.now(TIMEZONE)
    current_day = now.weekday()
    current_time = now.time()

    LOGGER.debug(
        f"Checking poll creation period: day={current_day}, time={current_time}, "
        f"morning_hour={MORNING_HOUR}"
    )

    # Sunday after 9 AM
    if current_day == Weekday.SUNDAY.value and current_time >= MORNING_HOUR:
        LOGGER.debug("Poll creation active: Sunday after 9 AM")
        return True
    # All day Monday
    if current_day == Weekday.MONDAY.value:
        LOGGER.debug("Poll creation active: Monday all day")
        return True
    # Tuesday before 9 AM
    if current_day == Weekday.TUESDAY.value and current_time < MORNING_HOUR:
        LOGGER.debug("Poll creation active: Tuesday before 9 AM")
        return True

    LOGGER.debug("Poll creation not active")
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

        # Check if this is a nomination week
        with self.bot.db.begin() as session:
            if not should_run_nominations_this_week(session):
                await interaction.response.send_message(
                    "Nominations are not open this week. "
                    "Nominations are open every other week.",
                    ephemeral=True,
                )
                return

        # Check if nominations are currently open
        if not is_nomination_period_active():
            await interaction.response.send_message(
                "Nominations are currently closed. "
                "Nominations are open from Thursday 9:00 AM to Sunday 9:00 AM.",
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
        with self.bot.db.begin() as session:
            last_nominations_open = get_last_nomination_open_date(session)

        LOGGER.debug(f"Last nominations open date: {last_nominations_open}")

        if not last_nominations_open:
            return False

        now = datetime.now(TIMEZONE)
        today = now.date()

        # Calculate this week's Wednesday (the start of our week)
        # Wednesday is 2 in weekday()
        days_since_wednesday = (today.weekday() - 2) % 7
        this_wednesday = today - timedelta(days=days_since_wednesday)

        LOGGER.debug(f"This Wednesday's date: {this_wednesday}")
        LOGGER.debug(f"Checking if {last_nominations_open} >= {this_wednesday}")

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
        - Nominations: Thursday 9AM -> Sunday 9AM (every other week)
        - Poll Creation: Sunday 9AM -> Tuesday 9AM (every other week)
        """
        now = datetime.now(TIMEZONE)
        LOGGER.info(
            f"Checking missed tasks at {now}\n"
            f"    (weekday: {now.weekday()}, hour: {now.hour})"
        )

        with self.bot.db.begin() as session:
            # Check if this is a nomination week
            if not should_run_nominations_this_week(session):
                LOGGER.info("This is not a nomination week, skipping nomination tasks")
                return

            # Check for missed nomination opening (Thursday 9:00 AM - Sunday 9:00 AM)
            if (
                is_nomination_period_active()
                and not await self.have_sent_nominations_open_message()
            ):
                LOGGER.info("Running missed nominations open task")
                await self.send_nominations_open_message()

            if is_poll_creation_period_active() and not await self.have_created_poll():
                LOGGER.info("Running missed poll creation task")
                await self.create_poll()

    @tasks.loop(time=MORNING_HOUR)
    async def daily_check(self) -> None:
        """Check if we need to run weekly tasks today."""
        now = datetime.now(TIMEZONE)
        today = now.date()

        with self.bot.db.begin() as session:
            # Check if this is a nomination week
            if not should_run_nominations_this_week(session):
                LOGGER.info("This is not a nomination week, skipping nomination tasks")
                return

            # Thursday - Open nominations, if we haven't run it today
            if (
                now.weekday() == Weekday.THURSDAY.value
                and not await self.have_sent_nominations_open_message()
            ):
                await self.send_nominations_open_message()
                LOGGER.info(f"Ran Nominations Open Task on {today} during Daily Check")

            # Sunday - Create poll, if we haven't run it today
            elif (
                now.weekday() == Weekday.SUNDAY.value
                and not await self.have_created_poll()
            ):
                await self.create_poll()
                LOGGER.info(f"Ran Poll Creation Task on {today} during Daily Check")

    async def send_nominations_open_message(self) -> None:
        """Send a message to open nominations."""
        LOGGER.info("Attempting to send nominations open message...")
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
                    "Nominations will close on Sunday at 9:00 AM when voting begins.\n\n"
                    "Note: Nominations are open every other week."
                ),
                color=discord.Color.blue(),
            )
            embed.set_footer(text="You can have up to 2 nominations.")

            await channel.send(embed=embed)
            LOGGER.info("Sent nominations open message")

            # Only update last run date if message was sent successfully
            LOGGER.debug("Updating last run date in database...")
            with self.bot.db.begin() as session:
                LOGGER.debug(f"Using session: {session}")
                set_nomination(session)
                LOGGER.debug("Last run date updated in database")

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
                LOGGER.debug("Sending poll message...")
                poll_message = await channel.send(
                    content="# 🗳️ Format Voting 🗳️\n\nVote for next week's format!",
                    poll=poll,
                )
                LOGGER.debug(f"Poll message sent with ID: {poll_message.id}")

                # Store the poll ID and clear nominations
                LOGGER.debug("Clearing nominations...")
                clear_all_nominations(session)
                LOGGER.info(f"Created poll with {len(unique_formats)} format options")

                LOGGER.debug(f"Setting poll with message ID {poll_message.id}")
                LOGGER.debug(f"Using session: {session}")
                set_poll(session, poll_message.id)
                LOGGER.debug("Poll set in database")

            LOGGER.info("Successfully created poll")

        except Exception as e:
            LOGGER.error(f"Error creating poll: {e}", exc_info=True)
            raise

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

    @app_commands.command(
        name="debug-nominations", description="Debug information about nominations"
    )
    @app_commands.checks.has_role(Roles.MOD.role_id)
    @app_commands.guild_only()
    async def debug_nominations(self, interaction: discord.Interaction) -> None:
        """Show debug information about nominations and polls."""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        try:
            # Create embed for debug info
            embed = discord.Embed(
                title="🔍 Nomination Debug Information",
                color=discord.Color.blue(),
            )

            # Add current bot time
            current_time = datetime.now(TIMEZONE)
            embed.add_field(
                name="Current Time",
                value=(
                    f"```\n"
                    f"Time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                    f"Weekday: {current_time.strftime('%A')}\n"
                    f"Is Nomination Period Active: {is_nomination_period_active()}\n"
                    f"Is Poll Creation Period Active: "
                    f"{is_poll_creation_period_active()}\n"
                    f"```"
                ),
                inline=False,
            )

            # Get all nominations and dates
            with self.bot.db.begin() as session:
                nominations = get_all_nominations(session)
                active_poll_id = get_active_poll_id(session)
                last_poll_date = get_poll_last_run_date(session)
                last_nomination_date = get_last_nomination_open_date(session)

                # Add nominations section
                if nominations:
                    nominations_text = ""
                    for nom in nominations:
                        if not hasattr(nom, "user_id") or not hasattr(nom, "format"):
                            continue
                        user = interaction.guild.get_member(nom.user_id)
                        user_name = (
                            user.display_name
                            if user
                            else f"Unknown (ID: {nom.user_id})"
                        )
                        nominations_text += f"{user_name}: {nom.format}\n"

                    if nominations_text:
                        embed.add_field(
                            name=f"Nominations ({len(nominations)})",
                            value=f"```\n{nominations_text}```",
                            inline=False,
                        )
                    else:
                        embed.add_field(
                            name="Nominations",
                            value="```\nNo valid nominations in database```",
                            inline=False,
                        )
                else:
                    embed.add_field(
                        name="Nominations",
                        value="```\nNo nominations in database```",
                        inline=False,
                    )

                # Add task dates section
                dates_text = (
                    f"Last Poll Creation: "
                    f"{
                        last_poll_date.strftime('%Y-%m-%d')
                        if last_poll_date
                        else 'Never'
                    }\n"
                    f"Last Nominations Open: "
                    f"{
                        last_nomination_date.strftime('%Y-%m-%d')
                        if last_nomination_date
                        else 'Never'
                    }"
                )
                embed.add_field(
                    name="Task Dates",
                    value=f"```\n{dates_text}```",
                    inline=False,
                )

                # Add active poll section
                poll_status = (
                    f"Active Poll ID: {active_poll_id}"
                    if active_poll_id
                    else "No active poll"
                )
                embed.add_field(
                    name="Poll Status", value=f"```\n{poll_status}```", inline=False
                )

            # Add task status section
            nominations_open = await self.have_sent_nominations_open_message()
            poll_created = await self.have_created_poll()

            embed.add_field(
                name="Task Status",
                value=(
                    f"```\n"
                    f"have_sent_nominations_open_message: {nominations_open}\n"
                    f"have_created_poll: {poll_created}\n"
                    f"```"
                ),
                inline=False,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            LOGGER.error(f"Error in debug-nominations command: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Error retrieving debug information. Check logs for details.",
                ephemeral=True,
            )


async def setup(bot: Magic512Bot) -> None:
    """Load the Nomination cog."""
    await bot.add_cog(Nomination(bot))
