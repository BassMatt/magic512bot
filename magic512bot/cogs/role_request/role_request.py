from enum import StrEnum
from typing import List

import discord
from config import LOGGER, ROLE_REQUEST_CHANNEL_ID
from discord import app_commands
from discord.ext import commands
from main import Magic512Bot
from services.role_request import add_user_sweat_role

# from services.role_request import add_user_role, remove_user_role
from sqlalchemy.orm import Session, sessionmaker
from sweat import (
    process_user_milestone_roles,
    sync_user_sweat_roles,
)

COMPETITIVE_ROLES = {
    "RC Qualified": 1323031728238891100,
    "Pro Tour": 1338683101571977226,
}

SWEAT_ROLES = {
    "Standard Sweat": 1333297150192259112,
    "Pioneer Sweat": 1316976975138787459,
    "Modern Sweat": 1333297420456431646,
    "Legacy Sweat": 1333297655857807361,
    "Vintage Sweat": 1333297998595358804,
    "Pauper Sweat": 1333302285404471409,
    "Cube Sweat": 1333300770891759637,
    "Limited Sweat": 1333300276781645836,
}

MILESTONE_ROLES = {
    "OmniSweat": 1333322766362873927,
    "Sweat Lord": 1333301233670160435,
    "Sweat Knight": 1333322555465142353,
}

ALLOWED_ROLE_REQUESTS = COMPETITIVE_ROLES | SWEAT_ROLES


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

    # Competitive Roles
    RC_QUALIFIED = "RC Qualified"
    PRO_TOUR = "Pro Tour"


class RoleRequestView(discord.ui.View):
    def __init__(
        self, db: sessionmaker[Session], user_id: int, role_id: int, reason: str
    ):
        super().__init__(timeout=None)
        self.db = db
        self.user_id = user_id
        self.role_id = role_id
        self.reason = reason

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Get the role and member
        if not (guild := interaction.guild):
            await interaction.response.send_message(
                "Unable to find guild information!", ephemeral=True
            )
            return

        requested_role = guild.get_role(self.role_id)
        member = guild.get_member(self.user_id)

        if requested_role and member:
            try:
                if member.get_role(self.role_id):
                    await interaction.response.send_message(
                        "User already has this role!", ephemeral=True
                    )
                    return

                sync_user_sweat_roles(member, self.db)

                # Add Sweat Role to member, and db
                LOGGER.info("Adding Requested Role to Discord Member")
                await member.add_roles(requested_role)
                with self.db.begin() as session:
                    add_user_sweat_role(session, member.id, requested_role.name)
                LOGGER.info("Successfully Added Requested Role to Discord Member")

                # DM the user
                await member.send(
                    f"Your request for the role {requested_role.name} "
                    + "has been approved! 🎉"
                )

                await process_user_milestone_roles(member, guild, self.db)

                # Send confirmation
                await interaction.response.send_message(
                    f"✅ {interaction.user.mention} Approved role"
                    + f" {requested_role.name} for {member.mention}",
                    allowed_mentions=discord.AllowedMentions.none(),
                )

                # Disable the button
                self.disable_buttons()
                if message := interaction.message:
                    await message.edit(view=self)

            except discord.HTTPException:
                await interaction.response.send_message(
                    "❌ Failed to add role. Please check bot permissions.",
                    ephemeral=True,
                )
        else:
            await interaction.response.send_message(
                "❌ Could not find role or member.", ephemeral=True
            )

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get the role and member
        if not (guild := interaction.guild):
            await interaction.response.send_message(
                "Unable to find guild information!", ephemeral=True
            )
            return

        requested_role = guild.get_role(self.role_id)
        member = guild.get_member(self.user_id)
        if requested_role and member:
            # Send confirmation
            await interaction.response.send_message(
                f"{interaction.user.mention} Denied role {requested_role.name}"
                + f" for {member.mention}",
                allowed_mentions=discord.AllowedMentions.none(),
            )

            try:
                await member.send(
                    f"Your request for the role {requested_role.name} has been denied."
                )
            except discord.HTTPException:
                pass  # User might have DMs disabled

        self.disable_buttons()

    def disable_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


class RoleRequest(commands.Cog):
    def __init__(self, bot):
        self.bot: Magic512Bot = bot

    @app_commands.command(name="monarch-assign")
    @app_commands.describe(to="the team member who will receive Monarch")
    @app_commands.checks.has_role(Roles.THE_MONARCH.value)
    @app_commands.guild_only()
    async def give_monarch(self, interaction: discord.Interaction, to: discord.Member):
        # Ensure we're in a guild
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        # Explicitly cast interaction.user to Member
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Failed to fetch your member information!", ephemeral=True
            )
            return

        # Fetch the role by name
        role = discord.utils.get(interaction.guild.roles, name=Roles.THE_MONARCH)
        if not role:
            await interaction.response.send_message(
                f"Could not find the {Roles.THE_MONARCH} role!", ephemeral=True
            )
            return

        user = interaction.user
        if role not in user.roles:
            await interaction.response.send_message(
                "You do not have the Monarch", ephemeral=True
            )

        await user.remove_roles(
            role,
            reason=f"Monarch transfer initiated by {user.display_name}",
        )

        await to.add_roles(
            role, reason=f"Monarch transfer initiated by {user.display_name}"
        )

        await interaction.response.send_message(
            f"Successfully transferred {role.mention} role from you to {to.mention}",
            ephemeral=False,
        )

    async def role_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        # List of allowed role names
        return [
            app_commands.Choice(name=role, value=role)
            for role in ALLOWED_ROLE_REQUESTS.keys()
            if current.lower() in role.lower()
        ]

    @app_commands.command(name="role-request")
    @app_commands.describe(
        role_name="The Sweat role you want to request",
        reason="Brief description of how you earned it",
    )
    @app_commands.rename(role_name="role")
    @app_commands.autocomplete(role_name=role_autocomplete)
    @app_commands.guild_only()
    async def request_role(
        self, interaction: discord.Interaction, role_name: str, reason: str
    ) -> None:
        if not (guild := interaction.guild):
            await interaction.response.send_message(
                "Unable to obtain guild object where request made", ephemeral=True
            )
            return

        # Explicitly cast interaction.user to Member
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Failed to fetch your member information!", ephemeral=True
            )
            return

        # Check if role has "Sweat" in the name
        if role_name not in ALLOWED_ROLE_REQUESTS.keys():
            await interaction.response.send_message(
                "❌ You can only request Sweat Roles and RC Qualified",
                ephemeral=True,
            )
            return

        if not (role := discord.utils.get(guild.roles, name=role_name)):
            await interaction.response.send_message(
                "Unable to find role requested.",
                ephemeral=True,
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "You already have this role.", ephemeral=True
            )
            return

        # Create embed for moderators
        embed = discord.Embed(
            title="Role Request",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="User",
            value=f"{interaction.user.mention}",
            inline=False,
        )
        embed.add_field(name="Requested Role", value=role.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        # Get moderator channel

        role_request_channel = guild.get_channel(ROLE_REQUEST_CHANNEL_ID)
        if not role_request_channel or not isinstance(
            role_request_channel, discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ Could not find moderator channel. Please contact an administrator.",
                ephemeral=True,
            )
            return

        # Create view with approve button
        view = RoleRequestView(
            db=self.bot.db, user_id=interaction.user.id, role_id=role.id, reason=reason
        )

        LOGGER.info("Sending RoleRequestView to role_request_channel")
        # Send to moderator channel
        await role_request_channel.send(embed=embed, view=view)

        LOGGER.info("Successfully Sent RoleRequestView to role_request_channel")
        # Confirm to user
        await interaction.response.send_message(
            "✅ Your role request has been submitted! Moderators will review it soon.",
            ephemeral=True,
        )

    @app_commands.command(name="bootstrap-db")
    @app_commands.checks.has_role(Roles.MOD.value)
    @app_commands.guild_only()
    async def bootstrap_db(self, interaction: discord.Interaction):
        if not (guild := interaction.guild):
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Starting role synchronization. This may take a while...", ephemeral=True
        )

        for member in guild.members:
            if member.bot:
                continue

            sync_user_sweat_roles(member, self.bot.db)

        await interaction.followup.send(
            "Role synchronization complete!", ephemeral=True
        )

    @app_commands.command(name="leaderboard")
    @app_commands.guild_only()
    async def sweat_leaderboard(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        # Get sweat role counts for all members
        leaderboard = {}
        for member in interaction.guild.members:
            if member.bot:
                continue
            sweat_count = len(
                [role for role in member.roles if role.name in SWEAT_ROLES]
            )
            if sweat_count > 0:
                leaderboard[member.display_name] = sweat_count

        # Sort by count in descending order
        sorted_leaderboard = dict(
            sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
        )

        # Create embed
        embed = discord.Embed(
            title="Sweat Role Leaderboard",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        # Add leaderboard entries
        leaderboard_text = "\n".join(
            f"{idx + 1}. {name}: {count} sweat roles"
            for idx, (name, count) in enumerate(sorted_leaderboard.items())
        )

        if leaderboard_text:
            embed.description = leaderboard_text
        else:
            embed.description = "No sweat roles found!"

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleRequest(bot))
