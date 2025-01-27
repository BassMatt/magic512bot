from typing import Optional, List
import traceback
import discord
from discord import app_commands
from discord.ext  import commands
from errors import CardListInputError, CardNotFoundError
from util import parse_cardlist
from database import CardLoan, get_db
import datetime

from sqlalchemy import select, delete


from util import format_loanlist_output, format_bulk_loanlist_output
from magic512bot.cogs.role_request import Roles

class InsertCardLoansModal(discord.ui.Modal, title='LoanList'):
    loanlist = discord.ui.TextInput(
            label='LoanList',
            style=discord.TextStyle.long,
            required=True,
            max_length=1000,
            placeholder="1 Sheoldred, the Apocalypse\n3 Ketria Triome\n..."
    )
    def __init__(self, borrower: discord.Member, tag: str = ""):
        self.borrower = borrower 
        self.tag = tag
        super().__init__(title='LoanList')

    async def on_submit(self, interaction: discord.Interaction):
        cards_loaned = await insert_cardloans(
            card_list=self.loanlist.value.split("\n"), 
            lender=interaction.user.id, 
            borrower=self.borrower.id,
            borrower_name=self.borrower.display_name,
            tag=self.tag)
        await interaction.response.send_message(f"{interaction.user.mention} loaned **{cards_loaned}** cards to {self.borrower.mention}",
                                                allowed_mentions=discord.AllowedMentions.none())

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, CardListInputError):
            await interaction.response.send_message(str(error), ephemeral=True)
        else:
            print(traceback.format_exc())
            await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

class ReturnCardLoansModal(discord.ui.Modal, title='LoanList'):
    loanlist = discord.ui.TextInput(
            label='LoanList',
            style=discord.TextStyle.long,
            required=True,
            max_length=1000,
            placeholder="1 Sheoldred, the Apocalypse\n3 Ketria Triome\n..."
    )
    def __init__(self, borrower: discord.Member, tag: str = ""):
        self.borrower = borrower 
        self.tag = tag
        super().__init__(title='LoanList')

    async def on_submit(self, interaction: discord.Interaction):
        cards_returned = await return_cardloans(
            card_list=self.loanlist.value.split("\n"), 
            lender=interaction.user.id, 
            borrower=self.borrower.id, 
            tag=self.tag)
        await interaction.response.send_message(
            f"{self.borrower.mention} returned **{cards_returned}** cards to {interaction.user.mention}.",
            allowed_mentions=discord.AllowedMentions.none())

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, CardListInputError):
            await interaction.response.send_message(str(error), ephemeral=True)
        elif isinstance(error, CardNotFoundError):
            await interaction.response.send_message(str(error), ephemeral=True)
        else:
            print(traceback.format_exc())
            await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

class CardLender(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="loan", description="Loan a card")
    @app_commands.checks.has_role(Roles.TEAM.value)
    @app_commands.rename(borrower='to')
    @app_commands.describe(
        borrower='Team member you wish to lend cards to',
        tag='Order tag for bulk returning cards')
    async def loan_handler(self, interaction: discord.Interaction, borrower: discord.Member, tag: Optional[str] = ""):
        loan_modal = InsertCardLoansModal(borrower, tag)
        await interaction.response.send_modal(loan_modal)

    @app_commands.command(name="return", description="Return a card")
    @app_commands.checks.has_role(Roles.TEAM.value)
    @app_commands.describe(
        borrower='@mention member that is returning the loaned cards',
        tag='Return cards with a given order tag')
    @app_commands.rename(borrower="from")
    async def return_card_handler(interaction: discord.Interaction, borrower: discord.Member, tag: Optional[str] = ""):
        return_modal = ReturnCardLoansModal(borrower, tag)
        await interaction.response.send_modal(return_modal)

    @app_commands.command(name="bulkreturn", description="Return many cards")
    @app_commands.checks.has_role(Roles.TEAM.value)
    @app_commands.describe(
        borrower="@mention member that is returning the loaned cards",
        tag="Return cards with a given order tag")
    @app_commands.rename(borrower="from")
    async def bulk_return_Cards_handler(interaction: discord.Interaction, borrower: discord.Member, tag: Optional[str] = ""):
        returned_count = await bulk_return_cardloans(lender=interaction.user.id, borrower=borrower.id, tag=tag)
        await interaction.response.send_message(
            f"{borrower.mention} returned **{returned_count}** cards to {interaction.user.mention}.", 
            allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="getloans", description="Check loans from given borrower")
    @app_commands.checks.has_role(Roles.TEAM.value)
    @app_commands.describe(
        borrower="@mention member that is borrowing the cards",
        tag="Query for cards with given order tag")
    @app_commands.rename(borrower="to")
    async def get_loans_handler(interaction: discord.Interaction, borrower: discord.Member, tag: Optional[str] = ""):
        results = await get_cardloans(lender=interaction.user.id, borrower=borrower.id, tag=tag)
        response = f"{interaction.user.mention} has loaned **{sum(card.quantity for card in results)}** card(s) to {borrower.mention}\n\n"
        response += "```\n"+ format_loanlist_output(results) + "```"
        await interaction.response.send_message(response, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="bulkgetloans", description="Check loans from all borrowers")
    @app_commands.checks.has_role(Roles.TEAM.value)
    async def bulk_get_loans_handler(interaction: discord.Interaction):
        results = await bulk_get_cardloans(lender=interaction.user.id)
        response = "```\n" + format_bulk_loanlist_output(results) + "```"
        await interaction.response.send_message(response)


async def insert_cardloans(card_list: list[str], lender: int, borrower: int, borrower_name: str, tag: str = "") -> int:
    """
    Upserts Loan Objects into database based on if (Card Name + Tag) is already present

    Returns int, number of cards added
    """
    card_loans = []
    cards_added = 0
    for card_name, quantity in parse_cardlist(card_list).items():
        card_loans.append(CardLoan(
            created_at = datetime.datetime.now(),
            card = card_name,
            quantity = quantity,
            lender = lender,
            borrower = borrower,
            borrower_name = borrower_name,
            order_tag = tag 
        ))

    cards_added = sum(card.quantity for card in card_loans) 
    async for session in get_db():
        session.add_all(card_loans)
        await session.commit()
    
    return cards_added

async def bulk_return_cardloans(lender: int, borrower: int, tag: str = "") -> int:
    """
    Removes rows from card_loans table for a given lender
    based on if they match either of the two given parameters

    If no borrower / tag is specified, deletes all rows for a given lender.
    """
    affected_row_count = 0
    async for session in get_db():
        stmt = delete(CardLoan).where(
            CardLoan.lender == lender,
            CardLoan.borrower == borrower)
        if tag:
            stmt.where(CardLoan.order_tag == tag)
        
        affected_row_count = len(await session.execute(stmt).fetchall())
    return affected_row_count

async def return_cardloans(card_list: list[str], lender: int, borrower: int, tag: str) -> int:
    """
    Decrements quantity for each given card in card_list matching given parameters. If
    multiple rows are returned for a given card, decrements earliest matching rows first.

    Deletes card from CardLoan table if cards's quantity would become 0.

    Throws CardNotFoundError if card not found in loans table, or quantity would become < 0.

    Returns int, the number of cards successfully returned.
    """
    loans_to_return = parse_cardlist(card_list)
    not_found_errors = []
    total_return_count = 0

    async for session in get_db():
        for card_name, quantity_to_return in loans_to_return.items():
            card_query_stmt = select(CardLoan).where(
                CardLoan.card == card_name,
                CardLoan.lender == lender,
                CardLoan.borrower == borrower)
            if tag:
                card_query_stmt = card_query_stmt.where(CardLoan.order_tag == tag)
            
            result: List[CardLoan] = await session.scalars(card_query_stmt.order_by(CardLoan.created_at)).all()
            total_loaned_count = sum(card_loan.quantity for card_loan in result)

            if total_loaned_count < quantity_to_return:
                not_found_errors.append((card_name, quantity_to_return))
                continue

            for card_loan in result:
                if card_loan.quantity < quantity_to_return:
                    total_return_count += card_loan.quantity
                    quantity_to_return -= card_loan.quantity
                    await session.delete(card_loan)
                else:
                    card_loan.quantity -= quantity_to_return
                    total_return_count += quantity_to_return
                    break
            
        if len(not_found_errors) > 0:
            raise CardNotFoundError(card_errors=not_found_errors)

        return total_return_count 

async def get_cardloans(lender: int, borrower: int, tag: str) -> list[CardLoan]:
    """
    Returns a list of CardLoan objects that match the given parameters
    """

    statement = select(CardLoan).where(CardLoan.lender == lender, CardLoan.borrower == borrower)
    if tag:
        statement = statement.where(CardLoan.order_tag == tag)

    async for session in get_db():
        result = await session.scalars(statement).all()
        return list(result)

async def bulk_get_cardloans(lender: int):
    """
    Returns the list of all CardLoan objects for a given lender 
    """
    async for session in get_db():
        statement = select(CardLoan).where(CardLoan.lender == lender)
        result = await session.scalars(statement).all()
        return list(result)

async def delete_all_cardloans():
    async for session in get_db():
        statement = delete(CardLoan)
        result = await session.execute(statement)
        print(result.rowcount)

async def setup(bot):
    await bot.add_cog(CardLender(bot))