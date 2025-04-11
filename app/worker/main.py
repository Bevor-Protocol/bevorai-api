import os
import asyncio
import re
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, TypedDict
import logfire

from arq import ArqRedis, Retry
from arq.constants import default_queue_name, health_check_key_suffix
import logfire.propagate
import logfire.sampling
from tortoise import Tortoise

from app.config import TORTOISE_ORM, redis_settings
from app.utils.types.enums import NetworkEnum
from app.metrics import metrics_tasks_duration, metrics_tasks_total

from .tasks import get_deployment_contracts, handle_eval

load_dotenv()
logfire.configure(
    environment=os.getenv("RAILWAY_ENVIRONMENT_NAME", "development"),
    service_name="worker",
)


class LoggingMiddleware:
    HEALTH_REGEX = "j_complete=(?P<completed>[0-9]+).j_failed=(?P<failed>[0-9]+).j_retried=(?P<retried>[0-9]+).j_ongoing=(?P<ongoing>[0-9]+).queued=(?P<queued>[0-9]+)"  # noqa

    def __init__(self, ctx: dict):
        self.ctx = ctx
        self.scan = re.compile(self.HEALTH_REGEX)
        self.health_check_key = default_queue_name + health_check_key_suffix
        self._metrics_task: Optional[asyncio.Task] = None

    async def start(self):
        await self._start_metrics_task()

    def stop(self):
        if self._metrics_task is not None:
            self._metrics_task.cancel()

    async def _start_metrics_task(self) -> None:
        async def func_wrapper() -> None:
            """Wrapper function for a better error mesage when coroutine fails"""
            try:
                await self._observe_healthcheck()
            except Exception as err:
                logfire.exception(str(err))

        self._metrics_task = asyncio.create_task(func_wrapper())

    def log_enqueue_time(self, duration: float):
        metrics_tasks_duration.set(duration)

    def log_process_time(self, duration: float):
        metrics_tasks_duration.set(duration)

    async def _parse(self) -> dict:
        healthcheck = await self.ctx["redis"].get(self.health_check_key)
        if not healthcheck:
            return

        healthcheck = healthcheck.decode()

        info = self.scan.search(healthcheck)
        return info.groupdict()

    async def _observe_healthcheck(self):
        while True:
            # Sleep first to let worker initialize itself.
            await asyncio.sleep(5)

            await self._handle_health_logging()

    async def _handle_health_logging(self):
        data = await self._parse()
        if not data:
            return

        for k, v in data.items():
            value = int(v)
            metrics_tasks_total
            metrics_tasks_total.set(amount=value, attributes={"queue.type": k})


class JobContext(TypedDict):
    job_id: str
    job_try: int
    enqueue_time: datetime
    score: int
    redis: ArqRedis
    logging: LoggingMiddleware
    job_start_time: datetime


async def on_startup(ctx: JobContext):
    await Tortoise.init(config=TORTOISE_ORM)
    ctx["logging"] = LoggingMiddleware(ctx)
    await ctx["logging"].start()


async def on_shutdown(ctx: JobContext):
    await Tortoise.close_connections()
    ctx["logging"].stop()


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
    ctx["logging"].log_enqueue_time(diff.seconds)


async def on_job_end(ctx: JobContext):
    # gather the processing time (end_time - job_start_time)
    diff = datetime.now(tz=ctx["enqueue_time"].tzinfo) - ctx["job_start_time"]
    ctx["logging"].log_process_time(diff.seconds)


async def process_eval(ctx: JobContext, trace: logfire.propagate.ContextCarrier):
    # job_id was forcefully meant to match the audit_id
    audit_id = ctx["job_id"]
    with logfire.propagate.attach_context(trace):
        with logfire.span(f"processing audit {audit_id}"):
            response = await handle_eval(audit_id=audit_id)
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
