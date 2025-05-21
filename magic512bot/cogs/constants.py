from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar


@dataclass
class Role:
    """Represents a Discord role with its name, ID, and approval message."""

    name: str
    role_id: int
    message: str

    # Class-level storage for all roles
    _roles_by_id: ClassVar[dict[int, "Role"]] = {}
    _roles_by_name: ClassVar[dict[str, "Role"]] = {}

    def __post_init__(self):
        # Register the role in both lookup dictionaries
        self._roles_by_id[self.role_id] = self
        self._roles_by_name[self.name] = self

    @classmethod
    def from_id(cls, role_id: int) -> "Role | None":
        """Get a Role instance from a Discord role ID."""
        return cls._roles_by_id.get(role_id)

    @classmethod
    def from_name(cls, name: str) -> "Role | None":
        """Get a Role instance from a role name."""
        return cls._roles_by_name.get(name)

    @classmethod
    def get_message(cls, role_id: int) -> str | None:
        """Get the approval message for a role ID."""
        role = cls.from_id(role_id)
        return role.message if role else None


# Define all roles
class Roles:
    """Role definitions with their names, IDs, and messages."""

    # Team Roles
    THE_MONARCH = Role(
        name="The Monarch",
        role_id=1313309075680919552,
        message="{new} has slain {old} and has been crowned the new Monarch! \
            Give fealty while you can!",
    )

    # Sweat Roles
    STANDARD_SWEAT = Role(
        name="Standard Sweat",
        role_id=1333297150192259112,
        message="{user} now has {role}!",
    )
    PIONEER_SWEAT = Role(
        name="Pioneer Sweat",
        role_id=1316976975138787459,
        message="{user} now has {role}!",
    )
    MODERN_SWEAT = Role(
        name="Modern Sweat",
        role_id=1333297420456431646,
        message="{user} now has {role}!",
    )
    LEGACY_SWEAT = Role(
        name="Legacy Sweat",
        role_id=1333297655857807361,
        message="{user} now has {role}!",
    )
    VINTAGE_SWEAT = Role(
        name="Vintage Sweat",
        role_id=1333297998595358804,
        message="{user} now has {role}!",
    )
    PAUPER_SWEAT = Role(
        name="Pauper Sweat",
        role_id=1333302285404471409,
        message="{user} now has {role}!",
    )
    CUBE_SWEAT = Role(
        name="Cube Sweat", role_id=1333300770891759637, message="{user} now has {role}!"
    )
    LIMITED_SWEAT = Role(
        name="Limited Sweat",
        role_id=1333300276781645836,
        message="{user} now has {role}!",
    )
    VALUE_SWEAT = Role(
        name="Value Sweat",
        role_id=1349569141698203649,
        message="{user} now has {role}!",
    )

    # Milestone Roles
    OMNI_SWEAT = Role(
        name="OmniSweat",
        role_id=1333322766362873927,
        message=(
            "Behold! The legendary OmniSweat has emerged from the mist of perspiration! 🌊 "
            + "{user}'s dedication to sweating across all formats has transcended "
            + "mere mortal levels of moisture! They've achieved what others only dream of - "
            + "becoming the Supreme Sovereign of Sweat, the Grandmaster of Glow, the "
            + "Emperor of Evaporation! May their opponents tremble in fear as they face "
            + "the all-powerful force of their format-spanning sweatiness! 💦👑"
        ),
    )
    SWEAT_LORD = Role(
        name="Sweat Lord",
        role_id=1333301233670160435,
        message=(
            "Grovel, mortals! A new Sweat Lord has ascended to the throne of perspiration! "
            + "{user}'s dedication to the art of sweating has created a veritable monsoon "
            + "of moisture! Let us all bask in the glory of their sweat-soaked achievements! "
            + "May their opponents tremble at the sight of their curling body-hydrated "
            + "foils! 💦"
        ),
    )
    SWEAT_KNIGHT = Role(
        name="Sweat Knight",
        role_id=1333322555465142353,
        message=(
            "🎉 Hark! A new Sweat Knight has risen from the fields of perspiration! {user}'s "
            + "cardboard is now officially soaked in the holy waters of format-spanning "
            + "sweat! All envy their cardboard collection, they've truly proven their worth "
            + "through countless battles of capitalist valor!"
        ),
    )

    # Competitive Roles
    RC_QUALIFIED = Role(
        name="RC Qualified",
        role_id=1323031728238891100,
        message="Congrats to {user} for the RC Invite!",
    )
    PRO_TOUR = Role(
        name="Pro Tour",
        role_id=1338683101571977226,
        message="Congrats to {user} for the Pro Tour Invite!",
    )
    MOD = Role(
        name="Mod",
        role_id=1088496955514159267,
        message="WTF a new mod?",
    )

    TEAM = Role(
        name="Team",
        role_id=1157424223162216560,
        message="Someone has joined the team!",
    )


# Constants for role thresholds
OMNI_SWEAT_THRESHOLD = 8
SWEAT_LORD_THRESHOLD = 5
SWEAT_KNIGHT_THRESHOLD = 3

# Define role sets for easy access
SWEAT_ROLES = {
    Roles.STANDARD_SWEAT.name,
    Roles.PIONEER_SWEAT.name,
    Roles.MODERN_SWEAT.name,
    Roles.LEGACY_SWEAT.name,
    Roles.VINTAGE_SWEAT.name,
    Roles.PAUPER_SWEAT.name,
    Roles.CUBE_SWEAT.name,
    Roles.LIMITED_SWEAT.name,
    Roles.VALUE_SWEAT.name,
}

COMPETITIVE_ROLES = {
    Roles.RC_QUALIFIED.name,
    Roles.PRO_TOUR.name,
}

MILESTONE_ROLES = {
    Roles.OMNI_SWEAT.name,
    Roles.SWEAT_LORD.name,
    Roles.SWEAT_KNIGHT.name,
}

ALLOWED_ROLE_REQUESTS = SWEAT_ROLES | COMPETITIVE_ROLES


class Channels(IntEnum):
    TEAM_GENERAL_CHANNEL_ID = 1221910426019823676
    ROLE_REQUEST_CHANNEL_ID = 1333661909878050848
    WC_WEDNESDAY_CHANNEL_ID = 1347979962405097584
    MODERATOR_CHANNEL_ID = 1074040269642661910
    GENERAL_CHANNEL_ID = 1074039539737305108


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
