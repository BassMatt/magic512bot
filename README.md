# Magic 512 Bot

Bot that powers all the stuff that goes on in Magic512Discord.

## Card Lending

The Card Lending system allows users to track cards they've loaned to other members of the server. This is only available to Team members.

### Available Commands

- `/loan` - Loan cards to another server member. Opens a modal where you can enter a list of cards to loan.

  - Parameters:
    - `to`: The member who will borrow the cards
    - `tag`: Optional tag to categorize the loan (e.g., "Otters-standard")

- `/return` - Record cards being returned by a borrower. Opens a modal where you can enter a list of cards being returned.

  - Parameters:
    - `from`: The member who is returning cards
    - `tag`: Optional tag to filter which loans to return

- `/bulk-return` - Return all cards loaned to a specific member with a single command.

  - Parameters:
    - `from`: The member who is returning all cards
    - `tag`: Optional tag to filter which loans to return

- `/list-loans` - View all cards you've loaned to a specific member.

  - Parameters:
    - `to`: The member who borrowed the cards
    - `tag`: Optional tag to filter which loans to display

- `/list-all-loans` - View all cards you've loaned to all members.

## Role Requests

The Role Request system allows users to request and manage sweat roles that represent their format expertise. The following slash commands are available:

### Available Commands

- `/role-request` - Request a sweat role, or a competitive milestone.

  - Parameters:
    - `role`: The sweat role you want to request
    - `reason`: Why you're requesting this role

- `/leaderboard` - Display a leaderboard of members with the most sweat roles.

- `/monarch-assign` - Transfer the Monarch role from yourself to another team member.

  - Parameters:
    - `to`: The team member who will receive the Monarch role

  Note: This command can only be used by the current holder of the Monarch role.

### Milestone Roles

The system automatically assigns special milestone roles based on the number of sweat roles a user has:

- **Sweat Knight**: Awarded when a user has 3 or more sweat roles
- **Sweat Lord**: Awarded when a user has 5 or more sweat roles
- **OmniSweat**: Awarded when a user has 8 or more sweat roles (all available sweat roles)

## File Structure

The project follows a modular architecture to maintain separation of concerns:

- `cogs/` - Contains Discord command handlers organized by feature. These are Discord.py extension classes that register slash commands and handle user interactions. Cogs call service methods to perform business logic and database operations.

  - `card_lender.py` - Handles card loan commands
  - `role_request.py` - Manages role request functionality and sweat role tracking

- `models/` - Contains SQLAlchemy database models that define the schema

  - `base.py` - Base class for all models
  - `cardloan.py` - Model for tracking card loans between users
  - `user.py` - User data including sweat roles

- `services/` - Contains business logic and database operations

  - `card_lender.py` - Functions for managing card loans (insert, return, query)
  - `role_request.py` - Functions for managing user roles and sweat tracking

- `errors/` - Custom exception classes
- `config/` - Configuration settings and constants
- `main.py` - Bot initialization and entry point
