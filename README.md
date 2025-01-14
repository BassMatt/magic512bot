# Magic 512 Bot

### Local Setup

1. Run `poetry install`

2. Setup environment variables

You'll need several environment variables:
- `DB_CONNECTION_STRING`
- `TEST_GUILD_ID`
- `BOT_TOKEN`

3. Setup database

There are a couple database scripts that help with local testing. This is how I create the test sqlite database.

```
> cd magic512bot
> python

>>> import dbutil
>>> dbutil.create_tables()
```

3. Fix imports for vscode

In `.vscode/settings.json` you'll want to put
```
    "python.analysis.extraPaths": [
        "./card_lender"
    ],
```
so pylance is able to properly import things

### Future DEV Tasks
- Bounds checking on query return message, possibly alter view of data to fit within discord message limits?
- Setup Error Webhook to send to test/dev discord server with relevant stacktraces
- Auth on the endpoints (check if team role)
- Have length checking on query endpoint returns (if greater than 2k characters, upload file instead)
    - other option here is discord embeds, which have 6k char limit.
- Refactor code, actually write tests