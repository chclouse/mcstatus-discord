from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json
from sqlalchemy import create_engine
import sys

from src import bot
from src.models import Base, Session

config_file = 'config.json'


def main():
    # Read in the configuration.
    # TODO: separate out the configuration into its own object.
    with open(config_file) as f:
        config = json.loads(f.read())
    token = config['token']

    # Get the database and set up the schemas.
    db_type = config['database']['type']
    if db_type == 'sqlite':
        db_filename = config['database']['filename']
    else:
        print('Only SQLite3 databases are supported at this time.')
        sys.exit(1)
    db_engine = create_engine(f'{db_type}:///{db_filename}')
    Base.metadata.create_all(db_engine)
    Session.configure(bind=db_engine)

    # Set up the scheduler.
    # Maybe this should be done in the bot module?
    sched = AsyncIOScheduler()
    sched.add_job(lambda: bot.bot.loop.create_task(bot.update()), 'interval',
            seconds=60)
    bot.set_scheduler(sched)

    bot.bot.run(token)


if __name__ == '__main__':
    main()
