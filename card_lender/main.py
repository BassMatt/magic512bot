from typing import Optional
import traceback
import discord
from dotenv import load_dotenv
from discord import app_commands
import os
from api import create_loan
from errors import LoanListInputError

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

class LoanList(discord.ui.Modal, title='LoanList'):
    loanlist = discord.ui.TextInput(
            label='LoanList',
            style=discord.TextStyle.long,
            required=True,
            max_length=1000,
            placeholder="1 Sheoldred, the Apocalypse\n3 Ketria Triome\n..."
    )
    def __init__(self, borrower: discord.Member, tag: str):
        self.borrower = borrower 
        self.tag = tag
        super().__init__(title='LoanList')

    async def on_submit(self, interaction: discord.Interaction):
        create_loan(self.loanlist.value.split("\n"), interaction.user.id, self.borrower.id, self.tag)
        await interaction.response.send_message("Successfully committed transaction!")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, LoanListInputError):
            await interaction.response.send_message(str(error), ephemeral=True)
        else:
            print(traceback.format_exc())
            await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

client = MyClient()

@client.tree.command()
@app_commands.rename(borrower='to')
@app_commands.describe(
    borrower='Team member you wish to lend cards to',
    tag='Optional: Alphanumeric order tag for bulk returning cards')
async def loan(interaction: discord.Interaction, borrower: discord.Member, tag: Optional[str] = None):
    loan_modal = LoanList(borrower, tag)
    await interaction.response.send_modal(loan_modal)

if __name__ == "__main__":
    client.run(os.getenv("BOT_TOKEN"))