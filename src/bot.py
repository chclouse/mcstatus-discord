import asyncio
import datetime
import discord
from discord.ext import commands
import json
from mcstatus import MinecraftServer
import threading
import traceback

description = '''A Minecraft server status checker'''
notifier = None
notifier_file = 'persistent_notifier.json'
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
async def status(addr: str, persistence='single'):
    print("recieved command: !status {} {}".format(addr, persistence))

    status = get_status(addr)

    em = generate_embed(addr, status)
    if persistence == 'persistent':
        msg = await bot.say('*(Updated every minute.)*', embed=em)
        set_persistence_notifier(msg.channel.id, msg.id, addr, status)
    else:
        await bot.say(embed=em)


async def update():
    notifier = get_persistence_notifier()
    if notifier == {}:
        return
    
    channel = bot.get_channel(notifier['channel_id'])
    if channel is None:
        set_persistence_notifier(None, None, None, None)
        return
    
    try:
        message = await bot.get_message(channel, notifier['message_id'])
    except discord.errors.NotFound:
        set_persistence_notifier(None, None, None, None)
        return
    
    addr = notifier['hostname']
    status = get_status(addr)
    if notifier['last_status'] != status_to_dict(status):
        set_persistence_notifier(channel.id, message.id, addr, status)
        em = generate_embed(addr, status)
        await bot.edit_message(message, '*(Updated every minute.)*', embed=em)


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


def status_to_dict(status):
    if status is None:
        last = {'online': False}
    else:
        last = {
            'online': True,
            'players': status.players.online,
            'max': status.players.max,
            'sample': []
        }
        if status.players.sample is not None:
            last['sample'] = list([p.name for p in status.players.sample])
    return last


def load_persistence_notifier():
    with open(notifier_file) as f:
        return json.loads(f.read())


def get_persistence_notifier():
    global notifier
    if notifier is None:
        notifier = load_persistence_notifier()
    return notifier


def set_persistence_notifier(channel_id, msg_id, addr, status):
    global notifier

    save = False

    last = status_to_dict(status)
    if notifier is None or msg_id != notifier.get('message_id') or \
            channel_id != notifier.get('channel_id'):
        save = True

    if msg_id is not None:
        notifier = {
            'channel_id': channel_id,
            'message_id': msg_id,
            'hostname': addr,
            'last_status': last
        }
    else:
        notifier = {}

    if save:
        save_persistence_notifier()


def save_persistence_notifier():
    global notifier
    with open('persistent_notifier.json', 'w') as f:
        f.write(json.dumps(notifier))


def get_status(addr):
    server = MinecraftServer.lookup(addr)
    try:
        return server.status()
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__)
        return None


def main():
    with open(config_file) as f:
        config = json.loads(f.read())
    token = config['token']

    sched = AsyncIOScheduler()
    sched.add_job(lambda: bot.loop.create_task(update()), 'interval',
            seconds=60)

    bot.run(token)


if __name__ == '__main__':
    main()
