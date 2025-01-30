import asyncio
import logging

import anyio
from arq import create_pool, cron
from arq.connections import RedisSettings
from tortoise import Tortoise
from tortoise.transactions import in_transaction

from app.cronjobs.contract_scan import get_deployment_contracts
from app.db.config import TORTOISE_ORM
from app.db.models import Audit
from app.prometheus import logger
from app.tasks.eval import handle_eval, test_get
from app.utils.enums import AuditStatusEnum, AuditTypeEnum, NetworkEnum

from .tasks.webhook import handle_outgoing_webhook

# from dramatiq.middleware.prometheus import Prometheus


REDIS_SETTINGS = RedisSettings(host="redis", port=6379)


async def init_db(ctx):
    logging.info(TORTOISE_ORM)
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()


async def close_db(ctx):
    await Tortoise.close_connections()


# every_minute = crontab(minute="*/1")
# every_five_minutes = crontab(minute="*/5")


# @huey.on_startup()
# def open_db_connection():
#     if not Tortoise._inited:
#         logging.info("Initializing database connection...")
#         anyio.run(init_db)
#         logging.info("\n\n\nINITIALIZED\n\n\n")


# @huey.on_shutdown()
# def close_db_connection():
#     if Tortoise._inited:
#         logging.info("Closing database connection.")
#         anyio.run(close_db)
#         logging.info("CLOSED")


async def test(string):
    logging.info("SLEEPING")
    await anyio.sleep(1)
    logging.info("GETTING AUDIT")
    async with in_transaction() as conn:
        audit = await Audit.all().using_db(conn)
    if audit:
        logging.info(f"GOT AUDIT {str(audit[0].id)}")
    else:
        logging.info("NO AUDIT FOUND")
    await anyio.sleep(1)
    logging.info(f"SLEPT {string}")


async def test_print(ctx):
    logging.info(ctx)
    logging.info("IM CALLED")
    # logger.increment_cron()
    # anyio.run(test_get)
    await test("hello world")


# @huey.periodic_task(every_five_minutes, retries=1, priority=1)
# def scan_contracts():
#     for network in [NetworkEnum.ETH, NetworkEnum.ETH_SEPOLIA]:
#         try:
#             anyio.run(get_deployment_contracts, network)
#         except Exception as err:
#             logging.warning(err)
#             pass


# @huey.task(retries=3, priority=10)
# def process_webhook(audit_id: str, audit_status: AuditStatusEnum, webhook_url: str):
#     anyio.run(
#         handle_outgoing_webhook,
#         audit_id,
#         audit_status,
#         webhook_url,
#     )


async def process_eval(ctx, audit_id: str, code: str, audit_type: AuditTypeEnum):
    logging.info(code)
    await handle_eval(
        job_id=ctx["job_id"], audit_id=audit_id, code=code, audit_type=audit_type
    )


class WorkerSettings:
    functions = [process_eval]
    cron_jobs = [cron(test_print, second=30)]
    on_startup = init_db
    on_shutdown = close_db
    redis_settings = REDIS_SETTINGS
    allow_abort_jobs = True
