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
        "./magic512bot"
    ],
```
so pylance is able to properly import thing