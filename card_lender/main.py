import discord
from dotenv import load_dotenv
from discord import app_commands
import os


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)





intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
client.run(os.getenv("BOT_TOKEN"))

@client.event
async def on_ready():
    print(f'We have logged in as {self.client.user}')

@client.event
async def on_message(self, message):
    if message.author == self.client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

if __name__ == "__main__":
    load_dotenv()
    main()