import traceback

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.orm import Session, sessionmaker

from magic512bot.cogs.constants import Roles
from magic512bot.config import LOGGER
from magic512bot.errors import CardListInputError, CardNotFoundError
from magic512bot.main import Magic512Bot
from magic512bot.services.card_lender import (
    bulk_get_cardloans,
    bulk_return_cardloans,
    format_bulk_loanlist_output,
    format_loanlist_output,
    get_cardloans,
    insert_cardloans,
    return_cardloans,
)


class InsertCardLoansModal(discord.ui.Modal, title="LoanList"):
    loanlist: discord.ui.TextInput

    def __init__(self, db: sessionmaker[Session], borrower: discord.Member, tag: str):
        super().__init__()
        self.loanlist = discord.ui.TextInput(
            label="LoanList",
            style=discord.TextStyle.long,
            required=True,
            max_length=1000,
            placeholder="1 Sheoldred, the Apocalypse\n3 Ketria Triome\n...",
        )
        self.add_item(self.loanlist)
        self.db = db
        self.borrower = borrower
        self.tag = tag

    async def on_submit(self, interaction: discord.Interaction):
        with self.db.begin() as session:
            cards_loaned = insert_cardloans(
                session=session,
                card_list=self.loanlist.value.split("\n"),
                lender=interaction.user.id,
                borrower=self.borrower.id,
                borrower_name=self.borrower.display_name,
                tag=self.tag,
            )
            message = f"{interaction.user.mention} \
                loaned **{cards_loaned}** cards to \
                {self.borrower.mention}"
            await interaction.response.send_message(
                message, allowed_mentions=discord.AllowedMentions.none()
            )

    async def on_error(  # type: ignore[override]
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        if isinstance(error, CardListInputError):
            await interaction.response.send_message(str(error), ephemeral=True)
        else:
            LOGGER.info(traceback.format_exc())
            await interaction.response.send_message(
                "Oops! Something went wrong.", ephemeral=True
            )


class ReturnCardLoansModal(discord.ui.Modal, title="LoanList"):
    loanlist: discord.ui.TextInput

    def __init__(
        self, db: sessionmaker[Session], borrower: discord.Member, tag: str = ""
    ):
        super().__init__()
        self.loanlist = discord.ui.TextInput(
            label="LoanList",
            style=discord.TextStyle.long,
            required=True,
            max_length=1000,
            placeholder="1 Sheoldred, the Apocalypse\n3 Ketria Triome\n...",
        )
        self.add_item(self.loanlist)
        self.db = db
        self.borrower = borrower
        self.tag = tag

    async def on_submit(self, interaction: discord.Interaction):
        with self.db.begin() as session:
            try:
                cards_returned = return_cardloans(
                    session=session,
                    card_list=self.loanlist.value.split("\n"),
                    lender=interaction.user.id,
                    borrower=self.borrower.id,
                    tag=self.tag,
                )
                message = f"{self.borrower.mention} returned **{cards_returned}** \
                    cards to {interaction.user.mention}"
                await interaction.response.send_message(
                    message, allowed_mentions=discord.AllowedMentions.none()
                )
            except CardNotFoundError as e:
                await interaction.response.send_message(str(e), ephemeral=True)

    async def on_error(  # type: ignore[override]
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        if isinstance(error, CardListInputError):
            await interaction.response.send_message(str(error), ephemeral=True)
        elif isinstance(error, CardNotFoundError):
            await interaction.response.send_message(str(error), ephemeral=True)
        else:
            LOGGER.info(traceback.format_exc())
            await interaction.response.send_message(
                "Oops! Something went wrong.", ephemeral=True
            )


class CardLender(commands.Cog):
    def __init__(self, bot: Magic512Bot):
        self.bot: Magic512Bot = bot
        LOGGER.info("CardLender Cog Initialized")

    @app_commands.command(name="loan", description="Loan a card")
    @app_commands.checks.has_role(Roles.TEAM.role_id)
    @app_commands.describe(
        borrower="Team member you wish to lend cards to",
        tag="Order tag for bulk returning cards",
    )
    @app_commands.rename(borrower="to")
    async def loan_handler(
        self,
        interaction: discord.Interaction,
        borrower: discord.Member,
        tag: str | None = "",
    ):
        tag = tag if tag is not None else ""
        loan_modal = InsertCardLoansModal(self.bot.db, borrower, tag)
        await interaction.response.send_modal(loan_modal)

    @app_commands.command(name="return", description="Return a card")
    @app_commands.checks.has_role(Roles.TEAM.role_id)
    @app_commands.describe(
        borrower="@mention member that is returning the loaned cards",
        tag="Return cards with a given order tag",
    )
    @app_commands.rename(borrower="from")
    async def return_cards_handler(
        self,
        interaction: discord.Interaction,
        borrower: discord.Member,
        tag: str | None = "",
    ):
        tag = tag if tag is not None else ""
        return_modal = ReturnCardLoansModal(self.bot.db, borrower, tag)
        await interaction.response.send_modal(return_modal)

    @app_commands.command(name="bulk-return", description="Return many cards")
    @app_commands.checks.has_role(Roles.TEAM.role_id)
    @app_commands.describe(
        borrower="@mention member that is returning the loaned cards",
        tag="Return cards with a given order tag",
    )
    @app_commands.rename(borrower="from")
    async def bulk_return_cards_handler(
        self,
        interaction: discord.Interaction,
        borrower: discord.Member,
        tag: str | None = "",
    ):
        with self.bot.db.begin() as session:
            returned_count = bulk_return_cardloans(
                session=session,
                lender=interaction.user.id,
                borrower=borrower.id,
                tag=tag if tag is not None else "",
            )
            message = f"{borrower.mention} returned **{returned_count}** \
                cards to {interaction.user.mention}."
            await interaction.response.send_message(
                message,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @app_commands.command(
        name="list-loans", description="Check loans from given borrower"
    )
    @app_commands.checks.has_role(Roles.TEAM.role_id)
    @app_commands.describe(
        borrower="@mention member that you are loaning cards to",
        tag="Query for cards with given order tag",
    )
    @app_commands.rename(borrower="to")
    async def list_loans_handler(
        self,
        interaction: discord.Interaction,
        borrower: discord.Member,
        tag: str | None = "",
    ):
        with self.bot.db.begin() as session:
            results = get_cardloans(
                session=session,
                lender=interaction.user.id,
                borrower=borrower.id,
                tag=tag if tag is not None else "",
            )
            card_sum = sum(card.quantity for card in results)
            response = (
                f"{interaction.user.mention} has loaned"
                + f"**{card_sum}** card(s) to {borrower.mention}\n\n"
            )
            response += "```\n" + format_loanlist_output(results) + "```"
            await interaction.response.send_message(
                response, allowed_mentions=discord.AllowedMentions.none()
            )

    @app_commands.command(
        name="list-all-loans", description="Check loans from all borrowers"
    )
    @app_commands.checks.has_role(Roles.TEAM.role_id)
    async def list_all_loans_handler(self, interaction: discord.Interaction):
        with self.bot.db.begin() as session:
            results = bulk_get_cardloans(session=session, lender=interaction.user.id)
            response = "```\n" + format_bulk_loanlist_output(results) + "```"
            await interaction.response.send_message(response)


async def setup(bot: Magic512Bot) -> None:
    await bot.add_cog(CardLender(bot))  # type: ignore
