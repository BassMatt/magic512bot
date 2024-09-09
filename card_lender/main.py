from typing import Optional
import traceback
import discord
from dotenv import load_dotenv
from discord import app_commands
import os
from errors import CardListInputError

import db
from util import format_loanlist_output

load_dotenv()

MY_GUILD=discord.Object(id=os.getenv("TEST_GUILD_ID"))

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    # Syncs guild commands to specified guild
    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

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
        db.insert_cardloans(
            cards=self.loanlist.value.split("\n"), 
            lender=interaction.user.id, 
            borrower=self.borrower.id, 
            order_tag=self.tag)
        await interaction.response.send_message("Successfully committed transaction!")

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
        db.delete_cardloans(
            card_list=self.loanlist.value.split("\n"), 
            lender=interaction.user.id, 
            borrower=self.borrower.id, 
            order_tag=self.tag)
        await interaction.response.send_message("Successfully committed transaction!")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, CardListInputError):
            await interaction.response.send_message(str(error), ephemeral=True)
        else:
            print(traceback.format_exc())
            await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)



client = MyClient()

@client.tree.command(name="loan")
@app_commands.rename(borrower='to')
@app_commands.describe(
    borrower='Team member you wish to lend cards to',
    tag='Order tag for bulk returning cards')
async def loan(interaction: discord.Interaction, borrower: discord.Member, tag: Optional[str] = ""):
    loan_modal = InsertCardLoansModal(borrower, tag)
    await interaction.response.send_modal(loan_modal)

@client.tree.command(name="return")
@app_commands.describe(
    borrower='@mention member that has returned the cards',
    tag='Return cards with a given order tag')
async def return_cards(interaction: discord.Interaction):
    pass

@client.tree.command(name="bulkreturn")
@app_commands.describe(
    borrower="Team member that is borrowing the cards",
    tag="Return cards with a given order tag")
@app_commands.rename(borrower="from")
async def bulk_return_Cards(interaction: discord.Interaction, borrower: discord.Member, tag: Optional[str]=""):
    pass

@client.tree.command(name="getloans")
@app_commands.describe(
    borrower="Team member that is borrowing the cards",
    tag="Query for cards with given order tag")
@app_commands.rename(borrower="from")
async def get_loans(interaction: discord.Interaction, borrower: discord.Member, tag: Optional[str] = ""):
    """
    Query for cards loaned to a given borrower.

    Args:
        - borrower: the @mention discord user that cards are loaned to
        - tag: optional, narrows results to loans with given tag

    On Success, sends persistent message listing all cards for a given borrower in table format.
    """
    results = db.get_cardloans(lender=interaction.user.id, borrower=borrower.id, tag=tag)
    response = f"{interaction.user.mention} has loaned **{sum(card.quantity for card in results)}** card(s) to {borrower.mention}\n\n"
    response += "```\n"+ format_loanlist_output(results) + "```"
    await interaction.response.send_message(response, allowed_mentions=discord.AllowedMentions.none())

@client.tree.command(name="bulkgetloans")
async def bulk_get_loans(interaction: discord.Interaction):
    pass


if __name__ == "__main__":
    client.run(os.getenv("BOT_TOKEN"))