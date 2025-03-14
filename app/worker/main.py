import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, TypedDict

from arq import ArqRedis, Retry
from arq.constants import default_queue_name, health_check_key_suffix
from prometheus_client import start_http_server
from tortoise import Tortoise

from app.config import TORTOISE_ORM, redis_settings
from app.prometheus import logger
from app.utils.types.enums import NetworkEnum

# from app.prometheus import logger
from .tasks import get_deployment_contracts, handle_eval

logging.basicConfig(level=logging.INFO)


class PrometheusMiddleware:
    HEALTH_REGEX = "j_complete=(?P<completed>[0-9]+).j_failed=(?P<failed>[0-9]+).j_retried=(?P<retried>[0-9]+).j_ongoing=(?P<ongoing>[0-9]+).queued=(?P<queued>[0-9]+)"  # noqa

    def __init__(self, ctx: dict):
        self.ctx = ctx
        self.scan = re.compile(self.HEALTH_REGEX)
        self.health_check_key = default_queue_name + health_check_key_suffix
        self._metrics_task: Optional[asyncio.Task] = None

    async def start(self):
        try:
            start_http_server(9192, addr="::")
        except Exception:
            logging.error("issue starting http server for prometheus")
            pass
        await self.__start_metrics_task()

    def stop(self):
        if self._metrics_task is not None:
            self._metrics_task.cancel()

    async def __start_metrics_task(self) -> None:
        async def func_wrapper() -> None:
            """Wrapper function for a better error mesage when coroutine fails"""
            try:
                await self.__observe_healthcheck()
            except Exception as e:
                logging.error(e)

        self._metrics_task = asyncio.create_task(func_wrapper())

    def log_enqueue_time(self, duration: float):
        logger.tasks_enqueue_duration.observe(duration)

    def log_process_time(self, duration: float):
        logger.tasks_duration.observe(duration)

    async def __parse(self) -> dict:
        healthcheck = await self.ctx["redis"].get(self.health_check_key)
        if not healthcheck:
            return

        healthcheck = healthcheck.decode()

        info = self.scan.search(healthcheck)
        return info.groupdict()

    async def __observe_healthcheck(self):
        while True:
            # Sleep first to let worker initialize itself.
            await asyncio.sleep(5)
            logging.info("[arq_prometheus] Gathering metrics (interval 5s)")

            await self.__handle_health_logging()

    async def __handle_health_logging(self):
        data = await self.__parse()
        if not data:
            return

        for k, v in data.items():
            value = int(v)
            logger.tasks_info.labels(type=k).set(value)


class JobContext(TypedDict):
    job_id: str
    job_try: int
    enqueue_time: datetime
    score: int
    redis: ArqRedis
    prometheus: PrometheusMiddleware
    job_start_time: datetime


async def on_startup(ctx: JobContext):
    await Tortoise.init(config=TORTOISE_ORM)
    ctx["prometheus"] = PrometheusMiddleware(ctx)
    await ctx["prometheus"].start()


async def on_shutdown(ctx: JobContext):
    await Tortoise.close_connections()
    ctx["prometheus"].stop()


async def scan_contracts(ctx: JobContext):
    try:
        for network in [NetworkEnum.ETH, NetworkEnum.ETH_SEPOLIA]:
            await get_deployment_contracts(network)
    except Exception:
        raise Retry(defer=ctx["job_try"] * 5)


async def on_job_start(ctx: JobContext):
    # Gather the enqueue time (job_start_time - enqueue_time)
    ctx["job_start_time"] = datetime.now(tz=ctx["enqueue_time"].tzinfo)
    diff = ctx["job_start_time"] - ctx["enqueue_time"]
    ctx["prometheus"].log_enqueue_time(diff.seconds)


async def on_job_end(ctx: JobContext):
    # gather the processing time (end_time - job_start_time)
    diff = datetime.now(tz=ctx["enqueue_time"].tzinfo) - ctx["job_start_time"]
    ctx["prometheus"].log_process_time(diff.seconds)


# @huey.task(retries=3, priority=10)
# def process_webhook(audit_id: str, audit_status: AuditStatusEnum, webhook_url: str):
#     anyio.run(
#         handle_outgoing_webhook,
#         audit_id,
#         audit_status,
#         webhook_url,
#     )


async def process_eval(ctx: JobContext):
    # job_id was forcefully meant to match the audit_id
    response = await handle_eval(audit_id=ctx["job_id"])
    return response


async def mock(ctx: JobContext):
    await asyncio.sleep(3)
    return 2


class WorkerSettings:
    functions = [process_eval, mock]
    on_startup = on_startup
    on_shutdown = on_shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end
    redis_settings = redis_settings
    allow_abort_jobs = True
    health_check_interval = 10
