import asyncio
import datetime
import logging

from apscheduler.events import (
    EVENT_JOB_ADDED,
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    JobEvent,
    JobExecutionEvent,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from rq import Queue

from .cache import redis_client

logging.basicConfig(level=logging.INFO)

# pool = ConnectionPool(host="0.0.0.0", port="6379", db=0)
queue = Queue(connection=redis_client)  # use default queue
scheduler = AsyncIOScheduler()


def schedule_submited_callback(event: JobEvent):
    pass
    # logging.info(f"event with job id {event.job_id} submitted")


def schedule_executed_callback(event: JobExecutionEvent):
    pass
    # if event.exception:
    #     logging.info(f"event with job id {event.job_id} failed {event.traceback}")
    # else:
    #     logging.info(f"event with job id {event.job_id} completed")


def enqueue_job(func, *args, **kwargs):
    # Enqueue job in Redis Queue
    queue.enqueue(func, *args, **kwargs)


async def my_simple_task():
    print("I started", datetime.datetime.now())
    await asyncio.sleep(3)
    print("I finished", datetime.datetime.now())


async def my_other_simple_task():
    print("I'm the other job", datetime.datetime.now())


every_minute = CronTrigger.from_crontab("*/1 * * * *")

scheduler.add_listener(schedule_submited_callback, EVENT_JOB_ADDED)
scheduler.add_listener(schedule_executed_callback, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)


scheduler.add_job(enqueue_job, trigger=every_minute, args=[my_simple_task])
scheduler.add_job(enqueue_job, trigger=every_minute, args=[my_other_simple_task])
