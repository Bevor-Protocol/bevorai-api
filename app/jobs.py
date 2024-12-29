import asyncio
import datetime
import os

from redis import Redis
from rq import Queue
from rq_scheduler import Scheduler

# pool = ConnectionPool(host="0.0.0.0", port="6379", db=0)
redis_conn = Redis(host=os.getenv("REDIS_HOST"), port=6379)
queue = Queue(connection=redis_conn)  # use default queue
scheduler = Scheduler(queue=queue, connection=queue.connection)


async def my_simple_task():
    print("I started", datetime.datetime.now())
    await asyncio.sleep(3)
    print("I finished", datetime.datetime.now())


def scheduler_wrapper():
    scheduler.cron("*/1 * * * *", func=my_simple_task)


def runner():
    scheduler_wrapper()
    scheduler.run()
