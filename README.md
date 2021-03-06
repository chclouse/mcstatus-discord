# mcstatus-discord
A discord bot that gives the status of a Minecraft server and can update statuses periodically.

## Configuring
Start by copying the file `config.json.example` to `config.json`.

Next, you'll need a discord token.
Instructions on obtaining a discord token can be found in [this][token] article.
Once you have the bot's token, it goes in the `token` field in `config.json`.

A database is required to support statuses that automatically update in the background.
Currently, only sqlite is supported, so the defaults should be fine.

Once you have configured as above and obtained the dependencies below, run with `python3 main.py` from the project root.

### Dependencies
This has been developed in Python 3.6.7.
You can get all the libraries through `pip3`/`pypi`.
Here are the libraries I use:
 * APScheduler
 * discord.py
 * mcstatus
 * SQLAlchemy

Additionally, you'll need sqlite3.
 
## Usage
At the present moment, there are only two commands:

`!status <server address>` -- This will get a one time status for the minecraft server.
This will not auto-update.

`!status <server address> persistent` -- This will post a status for the minecraft server.
The bot will then update it in the background every 60 seconds if the server status changes.

## Invite the Bot, Try it Out!

~~Click __here__ to invite the bot to your server.~~  
*(The invite link for the bot is temporarily disabled due to [issue #3](https://github.com/chclouse/mcstatus-discord/issues/3).)*

[token]: https://discordpy.readthedocs.io/en/rewrite/discord.html
[invite]: https://discordapp.com/api/oauth2/authorize?client_id=470819771353661440&permissions=0&scope=bot
