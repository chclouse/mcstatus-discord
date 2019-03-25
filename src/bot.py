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
    global sched
    sched = new_sched


@bot.event
async def on_ready():
    print("Logged in!")
    print(bot.user.name)
    print(bot.user.id)
    sched.start()


@bot.command()
async def status(addr: str, persistence='single', montype='passive'):
    print("recieved command: !status {} {} {}".format(addr, persistence,
        montype))

    status = get_status(addr)

    em = generate_embed(addr, status)
    if persistence == 'persistent' and montype == 'passive':
        msg = await bot.say('*(Updated every minute.)*', embed=em)
        session = models.Session()

        status_db = session.query(models.Status).filter_by(address=addr)\
                .one_or_none()
        sample_json = sample_json_from_status(status)

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

        monitor = models.Monitor(
                monitor_type=models.MonitorType.Passive,
                status_id=status_db.id,
                channel=msg.channel.id,
                message=msg.id)
        session.add(monitor)

        session.commit()

    elif persistence == 'persistent' and montype in ('DM', 'channel'):
        await bot.say('*Coming soon.*')
    elif persistence == 'persistent':
        await bot.say("*Sorry, I don't understand* `{}`.".format(montype))
    else:
        await bot.say(embed=em)


async def update():
    session = models.Session()
    for status_db in session.query(models.Status):
        addr = status_db.address
        status = get_status(addr)
        sample = sample_json_from_status(status)

        monitors = session.query(models.Monitor)\
                .filter_by(status_id=status_db.id)

        if monitors.count() == 0:
            print(f'Deleting Status for {status_db.address} from database.')
            session.delete(status_db)
            session.commit()
            continue

        if status_has_changed(status, status_db):
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

            for monitor in monitors:
                channel = bot.get_channel(monitor.channel)
                if channel is None:
                    print(f'Channel <{monitor.channel}> not found.')
                    print(f'Deleting {monitor} from database.')
                    session.delete(monitor)
                    session.commit()
                    continue
                
                if monitor.monitor_type == models.MonitorType.Passive:
                    try:
                        message = await bot.get_message(channel,
                                monitor.message)
                    except discord.errors.NotFound:
                        print(f'Message <{monitor.message}> not found.')
                        print(f'Deleting {monitor} from database.')
                        session.delete(monitor)
                        session.commit()
                        continue

                    em = generate_embed(addr, status)
                    await bot.edit_message(message,
                            '*(Updated every minute.)*', embed=em)

                else:
                    em = generate_embed(addr, status)
                    await bot.send_message(message, embed=em)


def generate_embed(addr, status):
    em = discord.Embed()
    em.title = addr
    em.set_footer(text="Status")
    em.timestamp = datetime.datetime.utcnow()
    
    if status is not None:
        em.description = ':white_check_mark: **Online**'
        em.colour = discord.Colour.green()
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
    else:
        em.description = ':x: **Offline**'
        em.colour = discord.Colour.red()
    
    return em


def get_status(addr):
    server = MinecraftServer.lookup(addr)
    try:
        return server.status()
    except Exception:
        return None


def status_has_changed(status_mc, status_db):
    if status_mc is None:
        return status_db.online
    else:
        return not(status_db.online and\
                status_mc.players.max == status_db.slots and\
                status_mc.players.online == status_db.online_players and\
                sample_json_from_status(status_mc) == status_db.sample)


def sample_json_from_status(status):
    if not(status is None) and 'players' in status.raw.keys() and \
            'sample' in status.raw['players'].keys():
        return json.dumps(status.raw['players']['sample'])
    else:
        return '[]'
