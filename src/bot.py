import asyncio
import datetime
import discord
from discord.ext import commands
import json
from mcstatus import MinecraftServer
from src import models
import threading
import traceback

description = '''A Minecraft server status checker'''
sched = None

bot = commands.Bot(command_prefix='!', description=description)

def set_scheduler(new_sched):
    """Allows a scheduler from APScheduler to be passed into the module."""
    global sched
    sched = new_sched


@bot.event
async def on_ready():
    """Print some helpful messages and start the scheduler."""
    print("Logged in!")
    print(bot.user.name)
    print(bot.user.id)
    sched.start()


@bot.command()
async def status(ctx, addr: str, persistence='single', montype='passive'):
    """Handler for the `!status` command.
    
    addr -- the server's address
    persistence -- `single` to post a status and stop, or `persistent` to keep
        updating
    montype -- only `passive` is supported as of yet. `active` will notify
        a change in status via DM
    """

    # Throughout this section, `status` is the current status obtained through
    # mcstatus, while `status_db` is the last known status queried from the
    # database and represented with a Status database model.
    print("recieved command: !status {} {} {}".format(addr, persistence,
        montype))
    status = get_status(addr)
    em = generate_embed(addr, status)

    if persistence == 'persistent' and montype == 'passive':
        msg = await ctx.send('*(Updated every minute.)*', embed=em)
        session = models.Session()

        # Get the last server status from the database. The address field is
        # set to `UNIQUE`, so there should be at most one.
        status_db = session.query(models.Status).filter_by(address=addr)\
                .one_or_none()
        sample_json = sample_json_from_status(status)

        # If there is no current record of the server, it's added here.
        if status_db is None and not(status is None):
            status_db = models.Status(
                    address=addr,
                    online=True,
                    timestamp=datetime.datetime.utcnow(),
                    slots=status.players.max,
                    online_players=status.players.online,
                    sample=sample_json)
            session.add(status_db)
        elif status_db is None and status is None:
            status_db = models.Status(
                    address=addr,
                    online=False,
                    timestamp=datetime.datetime.utcnow())
            session.add(status_db)

        session.commit()

        # Add the status monitor, which keeps up with the channel and message.
        monitor = models.Monitor(
                monitor_type=models.MonitorType.Passive,
                status_id=status_db.id,
                channel=msg.channel.id,
                message=msg.id)
        session.add(monitor)

        session.commit()

    # Error cases.
    elif persistence == 'persistent' and montype in ('DM', 'channel'):
        await ctx.send('*Coming soon.*')
    elif persistence == 'persistent':
        await ctx.send("*Sorry, I don't understand* `{}`.".format(montype))

    # Fall-through case (one-time status)
    else:
        await ctx.send(embed=em)


async def update():
    """Check each tracked server, and update the respective monitors.
    
    This function also drops any unwatched servers and inaccessible monitors.
    """
    session = models.Session()
    for status_db in session.query(models.Status):
        addr = status_db.address
        status = get_status(addr)
        sample = sample_json_from_status(status)

        monitors = session.query(models.Monitor)\
                .filter_by(status_id=status_db.id)

        # Prune the status for a server, if it has no associated monitors.
        if monitors.count() == 0:
            print(f'Deleting Status for {status_db.address} from database.')
            session.delete(status_db)
            session.commit()
            continue

        # Update the message only if the status changed.
        if status_has_changed(status, status_db):

            # Store the server status in the database.
            status_db.timestamp = datetime.datetime.utcnow()
            if status is None:
                status_db.online = False
                status_db.online_players = None
                status_db.slots = None
                status_db.sample = None
                session.commit()
            else:
                status_db.online = True
                status_db.online_players = status.players.online
                status_db.slots = status.players.max
                status_db.sample = sample
                session.commit()

            # Go through and update all the monitors.
            for monitor in monitors:
                #TODO: Migrate monitor.channel to an int type
                channel = bot.get_channel(int(monitor.channel))

                # Drop a monitor if its channel is no longer accessible.
                if channel is None:
                    print(f'Channel <{monitor.channel}> not found.')
                    print(f'Deleting {monitor} from database.')
                    session.delete(monitor)
                    session.commit()
                    continue

                if monitor.monitor_type == models.MonitorType.Passive:

                    # Get the message and drop the monitor if that fails.
                    try:
                        message = await channel.fetch_message(
                                int(monitor.message))
                    except discord.errors.NotFound:
                        print(f'Message <{monitor.message}> not found.')
                        print(f'Deleting {monitor} from database.')
                        session.delete(monitor)
                        session.commit()
                        continue

                    # Update the message.
                    em = generate_embed(addr, status)
                    await message.edit(content='*(Updated every minute.)*',
                            embed=em)

                else:
                    em = generate_embed(addr, status)
                    await bot.send_message(message, embed=em)


def generate_embed(addr, status):
    """Generate an embed for a status or status update.

    addr -- the server's address
    status -- an mcstatus object
    """

    # Some information that goes on every status message.
    em = discord.Embed()
    em.title = addr
    em.set_footer(text="Status")
    em.timestamp = datetime.datetime.utcnow()

    # If the server is online.
    if status is not None:
        em.description = ':white_check_mark: **Online**'
        em.colour = discord.Colour.green()

        # Convert the player sample list to a single string.
        if status.players.sample is None or status.players.sample == []:
            if status.players.online == 0:
                sample_str = '-'
            else:
                sample_str = '...'
        else:
            sample_str = '\n'.join([p.name for p in status.players.sample])
            if status.players.online > len(status.players.sample):
                sample_str += '\n...'
        em.add_field(name="{:d}/{:d} players online".format(
            status.players.online, status.players.max), value=sample_str,
            inline=False)

    # If the server is offline.
    else:
        em.description = ':x: **Offline**'
        em.colour = discord.Colour.red()
    
    return em


def get_status(addr):
    """Get the current status of a minecraft server.

    addr -- server address
    Returns an mcstatus object.
    """
    server = MinecraftServer.lookup(addr)
    try:
        return server.status()
    except Exception:
        return None


def status_has_changed(status_mc, status_db):
    """Checks if the status of a server has changed since the last status.

    status_mc -- recently obtained mcstatus
    status_db -- model for a status that was stored in the database
    """
    if status_mc is None:
        return status_db.online
    else:
        return not(status_db.online and\
                status_mc.players.max == status_db.slots and\
                status_mc.players.online == status_db.online_players and\
                sample_json_from_status(status_mc) == status_db.sample)


def sample_json_from_status(status):
    """Converts a sample list to json."""
    if not(status is None) and 'players' in status.raw.keys() and \
            'sample' in status.raw['players'].keys():
        return json.dumps(status.raw['players']['sample'])
    else:
        return '[]'
