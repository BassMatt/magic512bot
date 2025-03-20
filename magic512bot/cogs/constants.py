from enum import IntEnum, StrEnum

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
    "Value Sweat": 1349569141698203649,
}

MILESTONE_ROLES = {
    "OmniSweat": 1333322766362873927,
    "Sweat Lord": 1333301233670160435,
    "Sweat Knight": 1333322555465142353,
}


class Channels(IntEnum):
    TEAM_GENERAL_CHANNEL_ID = 1221910426019823676
    ROLE_REQUEST_CHANNEL_ID = 1333661909878050848
    WC_WEDNESDAY_CHANNEL_ID = 1347979962405097584
    MODERATOR_CHANNEL_ID = 1074040269642661910


ALLOWED_ROLE_REQUESTS = COMPETITIVE_ROLES | SWEAT_ROLES

# Constants for role thresholds
OMNI_SWEAT_THRESHOLD = 8
SWEAT_LORD_THRESHOLD = 5
SWEAT_KNIGHT_THRESHOLD = 3


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
    VALUE_SWEAT = "Value Sweat"

    SWEAT_KNIGHT = "Sweat Knight"  # 3 sweats
    SWEAT_LORD = "Sweat Lord"  # 5 sweats
    OMNI_SWEAT = "OmniSweat"  # 8 sweats

    # Competitive Roles
    RC_QUALIFIED = "RC Qualified"
    PRO_TOUR = "Pro Tour"


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
