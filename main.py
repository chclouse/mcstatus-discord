from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json

from src import bot

config_file = 'config.json'


def main():
    with open(config_file) as f:
        config = json.loads(f.read())
    token = config['token']

    sched = AsyncIOScheduler()
    sched.add_job(lambda: bot.bot.loop.create_task(bot.update()), 'interval',
            seconds=60)
    bot.set_scheduler(sched)

    bot.bot.run(token)


if __name__ == '__main__':
    main()
