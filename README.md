# Magic 512 Bot

Bot that powers all the stuff that goes on in Magic512Discord.

Has two main functions:
1. Card Lending - lets users track what cards they've lent to who
2. Role Requests - powers "sweat" role system that encourages players to try new magic formats

## Card Lending

## Role Requests

## File Structure

- `cogs` - this is a `discord.py` thing, but allows to break up application commands that power the bot by function. Files in this directory contain the "handlers" that call out to methods in `services` directly that perform the database operations
- `models` - database models
- `services` - methods that actually perform database operations, and generally expect a Session object

## Some Design Decisions
- Bot meant to run on one server, so stuck with keeping the database sessions syncronous. asyncio got too much of a pain to deal with - but there is a `async-refactor` branch for the adventurous
- DB operations are pretty infrequent, so I re-create a session for each transaction.
- tests might get done eventually
