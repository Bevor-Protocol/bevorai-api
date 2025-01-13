import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.utils.enums import NetworkEnum

from .worker import scan_contracts, test_print

logging.basicConfig(level=logging.INFO)


scheduler = AsyncIOScheduler()


every_minute = CronTrigger.from_crontab("*/1 * * * *")
every_five_minutes = CronTrigger.from_crontab("*/5 * * * *")

scheduler.add_job(
    test_print.send,
    trigger=every_minute,
)

scheduler.add_job(
    scan_contracts.send,
    trigger=every_five_minutes,
    args=[NetworkEnum.ETH],
)
scheduler.add_job(
    scan_contracts.send,
    trigger=every_five_minutes,
    args=[NetworkEnum.ETH_SEPOLIA],
)
