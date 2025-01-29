from enum import StrEnum

# import discord
# from config import ROLE_REQUEST_CHANNEL_ID
# from discord import app_commands
# from discord.ext import commands


class Roles(StrEnum):
    MOD = "Mod"

    # Team Roles
    TEAM = "Team"
    COUNCIL = "Council"
    HONORARY_TEAM_MEMBER = "Honorary Team Member"
    THE_MONARCH = "The Monarch"

    # Sweat Roles
    STANDARD_SWEAT = "Standard Sweat"
    PIONEER_SWEAT = "Pioneer Sweat"
    MODERN_SWEAT = "Modern Sweat"
    LEGACY_SWEAT = "Legacy Sweat"
    VINTAGE_SWEAT = "Vintage Sweat"
    PAUPER_SWEAT = "Pauper Sweat"
    CUBE_SWEAT = "Cube Sweat"
    LIMITED_SWEAT = "Limited Sweat"

    SWEAT_KNIGHT = "Sweat Knight"  # 3 sweats
    SWEAT_LORD = "Sweat Lord"  # 5 sweats
    OMNI_SWEAT = "OmniSweat"  # 8 sweats


# class RoleRequestModal(discord.ui.Modal, title="Role Request"):
#     role_name = discord.ui.TextInput(
#         label="Role Name", placeholder="Enter the role name you want"
#     )
#     reason = discord.ui.TextInput(
#         label="Reason",
#         style=discord.TextStyle.paragraph,
#         placeholder="Why do you deserve this role?",
#     )

#     async def on_submit(self, interaction: discord.Interaction):
#         await interaction.response.send_message(
#             "Your role request has been submitted!", ephemeral=True
#         )
#         await send_role_request_embed(
#             interaction, self.role_name.value, self.reason.value
#         )


# class ApproveButton(discord.ui.Button):
#     def __init__(self):
#         super().__init__(style=discord.ButtonStyle.green, label="Approve")

#     async def callback(self, interaction: discord.Interaction):
#         embed = interaction.message.embeds[0]
#         user_id = int(embed.footer.text.split()[-1])
#         role_name = embed.fields[0].value

#         guild = interaction.guild
#         user = guild.get_member(user_id)
#         role = discord.utils.get(guild.roles, name=role_name)

#         if role is None:
#             role = await guild.create_role(name=role_name)

#         await user.add_roles(role)
#         await interaction.response.send_message(
#             f"Role {role_name} has been granted to {user.mention}", ephemeral=True
#         )
#         await interaction.message.edit(view=None)


# class RoleRequest(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot

#     @app_commands.command(name="request_role", description="Request a role")
#     async def request_role(self, interaction: discord.Interaction):
#         await interaction.response.send_modal(RoleRequestModal())


# async def send_role_request_embed(
#     interaction: discord.Interaction, role_name: str, reason: str
# ):
#     embed = discord.Embed(title="Role Request", color=discord.Color.blue())
#     embed.add_field(name="Requested Role", value=role_name, inline=False)
#     embed.add_field(name="Reason", value=reason, inline=False)
#     embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
#     embed.set_footer(text=f"User ID: {interaction.user.id}")

#     channel = interaction.guild.get_channel(ROLE_REQUEST_CHANNEL_ID)
#     view = discord.ui.View()
#     view.add_item(ApproveButton())
#     await channel.send(embed=embed, view=view)


# async def setup(bot):
#     await bot.add_cog(RoleRequest(bot))
