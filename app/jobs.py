import asyncio
import hashlib
import logging

import httpx
from apscheduler.events import (
    EVENT_JOB_ADDED,
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    JobEvent,
    JobExecutionEvent,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.api.blockchain.scan import fetch_contract_source_code_from_explorer
from app.api.web3.provider import get_provider
from app.db.models import Contract
from app.utils.enums import ContractMethodEnum, NetworkEnum

from .queues import queue_low

logging.basicConfig(level=logging.INFO)


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


async def get_deployment_contracts(network: NetworkEnum):
    provider = get_provider(network)

    current_block = provider.eth.get_block_number()
    logging.info(f"Network: {network} --- Current block: {current_block}")
    receipts = provider.eth.get_block_receipts(current_block)

    deployment_addresses = []
    for receipt in receipts:
        if not receipt["to"]:
            logs = receipt["logs"]
            if logs:
                initial_log = logs[0]
                address = initial_log["address"]
                deployment_addresses.append(address)

    if not deployment_addresses:
        logging.info("no deployment addresses found")
        return

    tasks = []
    async with httpx.AsyncClient() as client:
        for address in deployment_addresses:
            tasks.append(
                asyncio.create_task(
                    fetch_contract_source_code_from_explorer(client, network, address)
                )
            )
    results = await asyncio.run(*tasks)

    to_create = []
    n_available = 0
    n_unavailable = 0
    for i, address in enumerate(deployment_addresses):
        result = results[i]
        if result:
            n_available += 1
            result: str
            to_create.append(
                Contract(
                    method=ContractMethodEnum.CRON,
                    contract_address=address,
                    contract_network=network,
                    contract_code=result,
                    contract_hash=hashlib.sha256(result.encode()).hexdigest(),
                )
            )
        else:
            n_unavailable += 1
            to_create.append(
                Contract(
                    method=ContractMethodEnum.CRON,
                    contract_address=address,
                    contract_network=network,
                    is_available=False,
                )
            )

    await Contract.bulk_create(*to_create)
    logging.info(
        f"Added {len(to_create)} contracts from {network}"
        f" --- {n_available} avaible source code"
        f" --- {n_unavailable} not avaiable source code"
    )


def enqueue_job(func, *args, **kwargs):
    # Enqueue job in Redis Queues
    queue_low.enqueue(func, *args, **kwargs)


every_minute = CronTrigger.from_crontab("*/1 * * * *")
every_five_minutes = CronTrigger.from_crontab("*/5 * * * *")

scheduler.add_listener(schedule_submited_callback, EVENT_JOB_ADDED)
scheduler.add_listener(schedule_executed_callback, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

scheduler.add_job(
    enqueue_job,
    trigger=every_five_minutes,
    args=[get_deployment_contracts, NetworkEnum.ETH],
)
scheduler.add_job(
    enqueue_job,
    trigger=every_five_minutes,
    args=[get_deployment_contracts, NetworkEnum.ETH_SEPOLIA],
)
