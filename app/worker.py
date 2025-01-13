import logging
import os

import anyio
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware.prometheus import Prometheus

# from dramatiq.results import Results
from dramatiq.results.backends.redis import RedisBackend

from app.cronjobs.contract_scan import get_deployment_contracts
from app.prometheus import logger
from app.utils.enums import AuditStatusEnum, NetworkEnum

from .tasks.webhook import handle_outgoing_webhook

# from dramatiq.middleware.prometheus import Prometheus


redis_broker = RedisBroker(url="redis://redis:6379")
redis_backend = RedisBackend(url="redis://redis:6379")
# redis_broker.add_middleware(Results(backend=redis_backend))
if os.environ.get("DRAMATIQ_PROCESS_TYPE") == "MainProcess":
    prometheus_middleware = Prometheus(
        bind="0.0.0.0", port=9192
    )  # Start only in the main process
    redis_broker.add_middleware(prometheus_middleware)
# redis_broker.add_middleware(Prometheus())
dramatiq.set_broker(redis_broker)


async def test(string):
    logging.info("SLEEPING")
    await anyio.sleep(1)
    logging.info(f"SLEPT {string}")


@dramatiq.actor(queue_name="low", max_retries=1)
def test_print():
    logging.info("IM CALLED")
    logger.increment_cron()
    anyio.run(test, "hello wrld")


@dramatiq.actor(queue_name="low", max_retries=1)
def scan_contracts(network: NetworkEnum):
    try:
        anyio.run(get_deployment_contracts, network)
    except Exception as err:
        logging.warning(err)
        pass


# Need to pass consume a serializable model as we rely on redis.
@dramatiq.actor(queue_name="high", max_retries=3)
def process_webhook(audit_id: str, audit_status: AuditStatusEnum, webhook_url: str):
    anyio.run(
        handle_outgoing_webhook,
        audit_id,
        audit_status,
        webhook_url,
    )
