import logging
from datetime import datetime
from typing import TypedDict

from arq import ArqRedis, Retry
from tortoise import Tortoise

from app.cronjobs.contract_scan import get_deployment_contracts
from app.db.config import TORTOISE_ORM

# from app.prometheus import logger
from app.tasks.eval import handle_eval
from app.utils.enums import AuditTypeEnum, NetworkEnum

from .cache import redis_settings


class JobContext(TypedDict):
    job_id: str
    job_try: int
    enqueue_time: datetime
    score: int
    redis: ArqRedis


async def on_startup(ctx: JobContext):
    logging.info(f"STARTING {ctx}")
    await Tortoise.init(config=TORTOISE_ORM)


async def on_shutdown(ctx: JobContext):
    await Tortoise.close_connections()


async def scan_contracts(ctx: JobContext):
    try:
        for network in [NetworkEnum.ETH, NetworkEnum.ETH_SEPOLIA]:
            await get_deployment_contracts(network)
    except Exception:
        raise Retry(defer=ctx["job_try"] * 5)


async def on_job_start(ctx: JobContext):
    logging.info("ON START")
    logging.info(ctx)


async def on_job_end(ctx: JobContext):
    logging.info("ON END")
    logging.info(ctx)


# @huey.task(retries=3, priority=10)
# def process_webhook(audit_id: str, audit_status: AuditStatusEnum, webhook_url: str):
#     anyio.run(
#         handle_outgoing_webhook,
#         audit_id,
#         audit_status,
#         webhook_url,
#     )


async def process_eval(ctx: JobContext, contract_id: str, audit_type: AuditTypeEnum):
    response = await handle_eval(
        audit_id=ctx["job_id"], contract_id=contract_id, audit_type=audit_type
    )
    return response


class WorkerSettings:
    functions = [process_eval]
    # cron_jobs = [
    #     cron(scan_contracts, second=0, run_at_startup=True, max_tries=2),
    # ]
    on_startup = on_startup
    on_shutdown = on_shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end
    redis_settings = redis_settings
    allow_abort_jobs = True
    health_check_interval = 10
