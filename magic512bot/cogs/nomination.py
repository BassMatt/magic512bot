import datetime
from enum import Enum

import discord
from discord import app_commands
from discord.ext import commands, tasks

from magic512bot.config import LOGGER, WC_WEDNESDAY_CHANNEL_ID
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
    get_last_run_date,
    set_active_poll_id,
    set_last_run_date,
)


class Weekday(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


MORNING_HOUR = 9
MAX_USER_NOMINATIONS = 2


def is_nomination_period_active() -> bool:
    """
    Check if the nomination period is currently active.
    Nominations are open from Thursday 9:00 AM to Sunday 9:00 AM.
    """
    now = datetime.datetime.now()
    current_day = now.weekday()
    current_hour = now.hour
    current_minute = now.minute

    # Check if it's Thursday after 9:00 AM
    if current_day == Weekday.THURSDAY.value and (
        current_hour > MORNING_HOUR
        or (current_hour == MORNING_HOUR and current_minute >= 0)
    ):
        return True
    # Check if it's Friday or Saturday (all day)
    elif current_day in [Weekday.FRIDAY.value, Weekday.SATURDAY.value]:
        return True
    # Check if it's Sunday before 9:00 AM
    elif current_day == Weekday.SUNDAY.value and (
        current_hour < MORNING_HOUR
        or (current_hour == MORNING_HOUR and current_minute == 0)
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
                channel = self.bot.get_channel(WC_WEDNESDAY_CHANNEL_ID)
                if channel and isinstance(channel, discord.TextChannel):
                    await channel.send(
                        f"🎲 **{interaction.user.display_name}** has nominated "
                        f"**{format}**!"
                    )
                else:
                    LOGGER.error(
                        f"Could not find channel with ID {WC_WEDNESDAY_CHANNEL_ID}"
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

    async def check_missed_tasks(self) -> None:
        """
        Check if any tasks were missed while the bot was down.

        Windows for missed tasks:
        - Nominations: Thursday 9AM -> Sunday 9AM
        - Poll Creation: Sunday 9AM -> Tuesday 9AM
        """
        now = datetime.datetime.now()
        LOGGER.info(
            f"Checking missed tasks at {now}\n"
            f"    (weekday: {now.weekday()}, hour: {now.hour})"
        )
        today = now.date()
        current_time = now.time()
        morning_time = datetime.time(hour=MORNING_HOUR, minute=0)

        with self.bot.db.begin() as session:
            last_thursday_run = get_last_run_date(session, "thursday_nominations")
            last_sunday_run = get_last_run_date(session, "sunday_poll")
            LOGGER.info(f"Last Thursday run: {last_thursday_run}")
            LOGGER.info(f"Last Sunday run: {last_sunday_run}")

            current_weekday = now.weekday()

            # Check for missed nomination opening (Thursday 9AM -> Sunday 9AM)
            if current_weekday in [
                Weekday.THURSDAY.value,
                Weekday.FRIDAY.value,
                Weekday.SATURDAY.value,
            ]:
                # If it's after 9AM on Thursday through Saturday
                if (
                    current_weekday == Weekday.THURSDAY.value
                    and current_time >= morning_time
                ) or current_weekday in [Weekday.FRIDAY.value, Weekday.SATURDAY.value]:
                    if not last_thursday_run or last_thursday_run < today:
                        LOGGER.info("Running missed Thursday nominations task")
                        await self.send_nominations_open_message()
            elif (
                current_weekday == Weekday.SUNDAY.value and current_time < morning_time
            ):
                # If it's before 9AM on Sunday
                thursday_date = today - datetime.timedelta(days=3)
                if not last_thursday_run or last_thursday_run < thursday_date:
                    LOGGER.info("Running missed Thursday nominations task")
                    await self.send_nominations_open_message()

            # Check for missed poll creation (Sunday 9AM -> Tuesday 9AM)
            is_sunday_after_morning = (
                current_weekday == Weekday.SUNDAY.value and current_time >= morning_time
            )
            is_monday = current_weekday == Weekday.MONDAY.value
            is_tuesday_before_morning = (
                current_weekday == Weekday.TUESDAY.value and current_time < morning_time
            )

            LOGGER.info(
                f"Poll creation conditions: sunday_after_9={is_sunday_after_morning}, "
                f"is_monday={is_monday}, tuesday_before_9={is_tuesday_before_morning}"
            )

            # Handle Sunday after 9AM or Monday (any time)
            if is_sunday_after_morning or is_monday:
                LOGGER.info(
                    f"In Sunday after 9AM/Monday window. \
                        Last run: {last_sunday_run}, Today: {today}"
                )
                if not last_sunday_run or last_sunday_run < today:
                    LOGGER.info("Running missed Sunday poll task")
                    await self.create_poll()
                else:
                    LOGGER.info("Poll already run today, skipping")

            # Handle Tuesday before 9AM
            elif is_tuesday_before_morning:
                sunday_date = today - datetime.timedelta(days=2)
                LOGGER.info(
                    f"In Tuesday before 9AM window. \
                        Last run: {last_sunday_run}, Sunday date: {sunday_date}"
                )
                if not last_sunday_run or last_sunday_run < sunday_date:
                    LOGGER.info("Running missed Sunday poll task")
                    await self.create_poll()
                else:
                    LOGGER.info("Poll already run for this window, skipping")

    @tasks.loop(time=datetime.time(hour=MORNING_HOUR, minute=0))
    async def daily_check(self) -> None:
        """Check if we need to run weekly tasks today."""
        now = datetime.datetime.now()
        today = now.date()

        with self.bot.db.begin() as session:
            last_thursday_run = get_last_run_date(session, "thursday_nominations")
            last_sunday_run = get_last_run_date(session, "sunday_poll")

            # Thursday - Open nominations
            if now.weekday() == Weekday.THURSDAY.value and last_thursday_run != today:
                await self.send_nominations_open_message()
                LOGGER.info(f"Ran Thursday task on {today}")

            # Sunday - Create poll
            elif now.weekday() == Weekday.SUNDAY.value and last_sunday_run != today:
                await self.create_poll()
                LOGGER.info(f"Ran Sunday task on {today}")

    async def send_nominations_open_message(self) -> None:
        """Send a message to open nominations."""
        channel = self.bot.get_channel(WC_WEDNESDAY_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            LOGGER.error(f"Could not find channel with ID {WC_WEDNESDAY_CHANNEL_ID}")
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
                today = datetime.datetime.now().date()
                set_last_run_date(session, "thursday_nominations", today)

        except Exception as e:
            LOGGER.error(f"Error sending nominations open message: {e}")
            raise

    async def create_poll(self) -> None:
        """Create a poll with all nominations."""
        LOGGER.info("Attempting to create poll...")
        channel = self.bot.get_channel(WC_WEDNESDAY_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            LOGGER.error(f"Could not find channel with ID {WC_WEDNESDAY_CHANNEL_ID}")
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
                    await channel.send(
                        "No nominations were submitted this week. "
                        "Skipping poll creation."
                    )
                    return

                # Calculate the date of the next Wednesday
                today = datetime.datetime.now().date()
                days_until_wednesday = (
                    2 - today.weekday()
                ) % 7  # 2 represents Wednesday
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
                    content="# 🗳️ Format Voting 🗳️\n\nVote for next week's format!",
                    poll=poll,
                )

                # Store the poll ID and clear nominations
                set_active_poll_id(session, poll_message.id)
                clear_all_nominations(session)
                LOGGER.info(f"Created poll with {len(unique_formats)} format options")

                # Only update last run date after successful poll creation
                today = datetime.datetime.now().date()
                set_last_run_date(session, "sunday_poll", today)

            LOGGER.info("Successfully created poll")

        except Exception as e:
            LOGGER.error(f"Error creating poll: {e}", exc_info=True)
            raise

    @commands.Cog.listener()
    async def on_poll_end(self, poll: discord.Poll) -> None:
        """Handle poll end event."""
        poll_id = (
            "No message"
            if not hasattr(poll, "message") or not poll.message
            else str(poll.message.id)
        )
        LOGGER.info(f"Poll end event received. Poll ID: {poll_id}")

        with self.bot.db.begin() as session:
            active_poll_id = get_active_poll_id(session)
            LOGGER.info(f"Active poll ID from database: {active_poll_id}")

            # Check if this poll is from a message we're tracking
            if not hasattr(poll, "message"):
                LOGGER.info("Poll has no message attribute, skipping")
                return
            if not poll.message:
                LOGGER.info("Poll message is None, skipping")
                return
            if poll.message.id != active_poll_id:
                LOGGER.info(
                    f"Poll ID {poll.message.id} doesn't match "
                    f"active poll ID {active_poll_id}, skipping"
                )
                return

            LOGGER.info("Format voting poll has ended. Processing results...")
            try:
                # Find the winning format
                LOGGER.info(f"Poll answers: {[answer.text for answer in poll.answers]}")
                LOGGER.info(
                    f"Victor answer: "
                    f"{poll.victor_answer.text if poll.victor_answer else 'No victor'}"
                )

                if not poll.victor_answer:
                    LOGGER.error("No victor answer found in poll")
                    await self.bot.send_error_message("No victor answer found in poll")
                    return

                winning_format = poll.victor_answer.text
                LOGGER.info(f"Winning format: {winning_format}")
                await self.create_event_for_format(winning_format.strip("*"))
            except Exception as e:
                LOGGER.error(f"Error processing poll end: {e}", exc_info=True)
                raise
            finally:
                # Reset the active poll ID in the database
                LOGGER.info("Resetting active poll ID to None")
                set_active_poll_id(session, None)

    async def create_event_for_format(self, format_name: str) -> None:
        """Create a Discord event for the winning format."""
        channel = self.bot.get_channel(WC_WEDNESDAY_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            LOGGER.error(f"Could not find channel with ID {WC_WEDNESDAY_CHANNEL_ID}")
            return

        try:
            # Calculate next Wednesday
            today = datetime.datetime.now().date()
            days_until_wednesday = (2 - today.weekday()) % 7  # 2 represents Wednesday
            next_wednesday = today + datetime.timedelta(days=days_until_wednesday)

            # Create event time at 7:00 PM next Wednesday
            event_time = datetime.datetime.combine(
                next_wednesday,
                datetime.time(hour=19, minute=0),  # 7:00 PM
            )
            event_end_time = event_time + datetime.timedelta(hours=2)

            # Create the event
            event = await channel.guild.create_scheduled_event(
                name=f"WC Wednesday: {format_name}",
                description=(
                    f"This week's WC Wednesday we're playing **{format_name}**!\n\n"
                ),
                start_time=event_time,
                end_time=event_end_time,
                location="Pat's Games",
                privacy_level=discord.PrivacyLevel.guild_only,
            )

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
    """Load the Nomination cog."""
    await bot.add_cog(Nomination(bot))
