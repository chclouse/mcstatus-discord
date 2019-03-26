# mcstatus-discord
A discord bot that gives the status of a Minecraft server and can update statuses periodically.

## Configuring
Start by copying the file `config.json.example` to `config.json`.

Next, you'll need a discord token.
I won't go into full detail here on how to setup a discord bot, but once you have the bot's token, it goes in the `token` field in `config.json`.

A database is required to support statuses that automatically update in the background.
Currently, only sqlite is supported, so the defaults should be fine.

Once you have configured as above and obtained the dependencies below, run with `python3 main.py` from the project root.

### Dependencies
You can get everything through `pip3`/`pypi`.
Here are the libraries I use:
 * APScheduler
 * discord.py
 * mcstatus
 * SQLAlchemy
 
## Usage
At the present moment, there are only two commands:

`!status <server address>` -- This will get a one time status for the minecraft server. This will not auto-update.

`!status <server address> persistent` -- This will post a status for the minecraft server. The bot will then update it in the background every 60 seconds if the server status changes.
