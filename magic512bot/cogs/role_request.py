import discord
from discord import app_commands
from discord.ext import commands

from magic512bot.config import LOGGER
from magic512bot.main import Magic512Bot

from .constants import (
    ALLOWED_ROLE_REQUESTS,
    MILESTONE_ROLES,
    OMNI_SWEAT_THRESHOLD,
    SWEAT_KNIGHT_THRESHOLD,
    SWEAT_LORD_THRESHOLD,
    SWEAT_ROLES,
    Channels,
    Role,
    Roles,
)


class RoleRequestView(discord.ui.View):
    def __init__(self, user_id: int, role_id: int, reason: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.role_id = role_id
        self.reason = reason

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        # Get the role and member
        if not (guild := interaction.guild):
            LOGGER.error(
                f"Guild not found for interaction from user {interaction.user.id}"
            )
            await interaction.response.send_message(
                "Unable to find guild information!", ephemeral=True
            )
            return

        LOGGER.info(
            f"Processing role approval - Role ID: {self.role_id}, "
            f"User ID: {self.user_id}, Guild ID: {guild.id}"
        )

        if not (requested_role := guild.get_role(self.role_id)):
            LOGGER.error(
                f"Role not found - Role ID: {self.role_id}, Guild ID: {guild.id}"
            )
            await interaction.response.send_message(
                "Unable to find role information!", ephemeral=True
            )
            return

        if not (member := guild.get_member(self.user_id)):
            LOGGER.error(
                f"Member not found - User ID: {self.user_id}, Guild ID: {guild.id}"
            )
            await interaction.response.send_message(
                "Unable to find member information!", ephemeral=True
            )
            return

        LOGGER.info(
            f"Found role and member - Role: {requested_role.name}, "
            f"Member: {member.display_name}"
        )

        try:
            if member.get_role(self.role_id):
                LOGGER.warning(
                    f"User already has role - User: {member.display_name}, "
                    f"Role: {requested_role.name}"
                )
                await interaction.response.send_message(
                    "User already has this role!", ephemeral=True
                )
                return

            # Add Sweat Role to member, and db
            LOGGER.info(
                f"Adding role {requested_role.name} to member {member.display_name}"
            )
            await member.add_roles(requested_role)

            LOGGER.info(
                f"Successfully added role {requested_role.name} to \
                    {member.display_name}"
            )

            # DM the user
            try:
                await member.send(
                    f"Your request for the role {requested_role.name} "
                    + "has been approved! 🎉"
                )
                LOGGER.info(f"Sent DM to user {member.display_name}")
            except discord.HTTPException:
                LOGGER.warning(
                    f"Could not send DM to user \
                        {member.display_name} - DMs may be disabled"
                )

            # Send confirmation
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} Approved role"
                + f" {requested_role.name} for {member.mention}",
                allowed_mentions=discord.AllowedMentions.none(),
            )

            LOGGER.info(f"Processing milestone roles for user {member.display_name}")
            role_for_message = await _process_user_milestone_roles(member, guild)
            if role_for_message is None:
                role_for_message = Role.from_id(requested_role.id)

            # Send Congratulations Message
            if not (general_channel := guild.get_channel(Channels.GENERAL_CHANNEL_ID)):
                await interaction.response.send_message(
                    "Unable to find general channel!", ephemeral=True
                )
                return

            if not isinstance(general_channel, discord.TextChannel):
                await interaction.response.send_message(
                    "Unable to find general channel!", ephemeral=True
                )
                return
            if role_for_message is not None:
                await self.send_congratulations_message(
                    member, general_channel, role_for_message
                )

            # Disable the button
            self.disable_buttons()
            if message := interaction.message:
                await message.edit(view=self)
                LOGGER.info("Disabled approval buttons")

        except discord.HTTPException as e:
            LOGGER.error(
                f"Discord HTTP error while adding role - "
                f"Role: {requested_role.name}, "
                f"Member: {member.display_name}, "
                f"Error: {e!s}"
            )
            await interaction.response.send_message(
                "❌ Failed to add role. Please check bot permissions.",
                ephemeral=True,
            )
        except Exception as e:
            LOGGER.error(
                f"Unexpected error while adding role - "
                f"Role: {requested_role.name}, "
                f"Member: {member.display_name}, "
                f"Error: {e!s}",
                exc_info=True,
            )
            await interaction.response.send_message(
                "❌ An unexpected error occurred. Please check the logs.",
                ephemeral=True,
            )

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
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

    async def send_congratulations_message(
        self, member: discord.Member, channel: discord.TextChannel, role: Role
    ) -> None:
        if role.name in SWEAT_ROLES:
            await channel.send(role.message.format(user=member.mention, role=role.name))
        else:
            await channel.send(role.message.format(user=member.mention))

    def disable_buttons(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


class RoleRequest(commands.Cog):
    def __init__(self, bot: Magic512Bot):
        self.bot = bot
        LOGGER.info("RoleRequest Cog Initialized")

    @app_commands.command(name="monarch-assign")
    @app_commands.describe(to="the team member who will receive Monarch")
    @app_commands.checks.has_role(Roles.THE_MONARCH.role_id)
    @app_commands.guild_only()
    async def give_monarch(
        self, interaction: discord.Interaction, to: discord.Member
    ) -> None:
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
                "You do not have the Monarch role to be able to assign it",
                ephemeral=True,
            )
            return

        await user.remove_roles(
            role,
            reason=f"Monarch transfer initiated by {user.display_name}",
        )

        await to.add_roles(
            role, reason=f"Monarch transfer initiated by {user.display_name}"
        )

        await interaction.response.send_message(
            f"Successfully transferred {role.mention} role from you to {to.mention}",
            ephemeral=True,
        )

        if channel := interaction.guild.get_channel(Channels.TEAM_GENERAL_CHANNEL_ID):
            if not isinstance(channel, discord.TextChannel):
                LOGGER.error(
                    f"Could not find text channel with ID "
                    f"{Channels.TEAM_GENERAL_CHANNEL_ID}"
                )
                return
            await channel.send(
                f"Successfully transferred {role.mention} role from "
                f"{user.mention} to {to.mention}"
            )
        return

    async def role_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        # List of allowed role names
        return [
            app_commands.Choice(name=role_name, value=role_name)
            for role_name in ALLOWED_ROLE_REQUESTS
            if current.lower() in role_name.lower()
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
        if role_name not in ALLOWED_ROLE_REQUESTS:
            await interaction.response.send_message(
                "❌ You can only request Sweat and Competitive Roles",
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
            value=f"{interaction.user.display_name}",
            inline=False,
        )
        embed.add_field(name="Requested Role", value=role.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        # Get moderator channel

        role_request_channel = guild.get_channel(Channels.ROLE_REQUEST_CHANNEL_ID)
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
            user_id=interaction.user.id, role_id=role.id, reason=reason
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
    @app_commands.checks.has_role(Roles.MOD.role_id)
    @app_commands.guild_only()
    async def bootstrap_db(self, interaction: discord.Interaction) -> None:
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

        await interaction.followup.send(
            "Role synchronization complete!", ephemeral=True
        )

    @app_commands.command(name="leaderboard")
    @app_commands.guild_only()
    async def sweat_leaderboard(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        # Get sweat role counts for all members
        count_to_members: dict[int, list[discord.Member]] = {}
        for member in interaction.guild.members:
            if member.bot:
                continue
            sweat_count = len(
                [role for role in member.roles if role.name in SWEAT_ROLES]
            )
            if sweat_count > 0:
                if sweat_count not in count_to_members:
                    count_to_members[sweat_count] = []
                count_to_members[sweat_count].append(member)

        # Create embed
        embed = discord.Embed(
            title="💦 Sweat Role Leaderboard 🏆",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        # Add entries sorted by count in descending order
        leaderboard_text = []
        for count in sorted(count_to_members.keys(), reverse=True):
            members = count_to_members[count]
            display_names = ", ".join(
                f"**{member.display_name}**"
                for member in sorted(members, key=lambda m: m.display_name)
            )
            role_text = "role" if count == 1 else "roles"
            leaderboard_text.append(f"**{count} {role_text}**: {display_names}")

        if leaderboard_text:
            embed.description = "\n".join(leaderboard_text)
        else:
            embed.description = "No sweat roles found! 💨"

        await interaction.response.send_message(embed=embed)


async def setup(bot: Magic512Bot) -> None:
    await bot.add_cog(RoleRequest(bot))


async def _clear_user_sweat_milestones(member: discord.Member) -> None:
    for role in member.roles:
        if role.name in MILESTONE_ROLES:
            await member.remove_roles(role)


async def _process_user_milestone_roles(
    member: discord.Member, guild: discord.Guild
) -> Role | None:
    member_roles = set(role.name for role in member.roles)
    sweat_role_count = len([role for role in member_roles if role in SWEAT_ROLES])

    # Add Milestone Role, if necessary
    role = None
    if sweat_role_count >= OMNI_SWEAT_THRESHOLD:
        if Roles.OMNI_SWEAT.name in member_roles:
            return None
        await _clear_user_sweat_milestones(member)
        if omnisweat_role := guild.get_role(Roles.OMNI_SWEAT.role_id):
            await member.add_roles(omnisweat_role)
            role = Roles.OMNI_SWEAT

    elif (
        sweat_role_count >= SWEAT_LORD_THRESHOLD
        and sweat_role_count < OMNI_SWEAT_THRESHOLD
    ):
        if Roles.SWEAT_LORD.name in member_roles:
            return None
        await _clear_user_sweat_milestones(member)
        if sweat_lord_role := guild.get_role(Roles.SWEAT_LORD.role_id):
            await member.add_roles(sweat_lord_role)
            role = Roles.SWEAT_LORD

    elif sweat_role_count >= SWEAT_KNIGHT_THRESHOLD:
        if Roles.SWEAT_KNIGHT.name in member_roles:
            return None
        await _clear_user_sweat_milestones(member)
        if sweat_knight_role := guild.get_role(Roles.SWEAT_KNIGHT.role_id):
            await member.add_roles(sweat_knight_role)
            role = Roles.SWEAT_KNIGHT
    return role
