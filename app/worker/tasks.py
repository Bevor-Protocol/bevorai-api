import asyncio
import logging
from datetime import datetime

import httpx

from app.api.services.blockchain import BlockchainService
from app.api.services.common import LlmPipeline
from app.client.web3 import Web3Client
from app.db.models import Audit, Contract
from app.schema.response import WebhookResponse, WebhookResponseData
from app.utils.enums import (
    AppTypeEnum,
    AuditStatusEnum,
    ContractMethodEnum,
    NetworkEnum,
)


async def handle_eval(audit_id: str):
    now = datetime.now()
    audit = await Audit.get(id=audit_id).select_related("app", "contract", "user")

    # only use pubsub for first-party applications.
    # otherwise, we can rely on webhooks or polling.
    should_publish = audit.app and audit.app.type == AppTypeEnum.FIRST_PARTY

    pipeline = LlmPipeline(
        input=audit.contract.raw_code,
        audit=audit,
        should_publish=should_publish,
        should_write_to_db=True,
    )

    audit.version = pipeline.version
    audit.status = AuditStatusEnum.PROCESSING
    await audit.save()

    try:
        await pipeline.generate_candidates()

        response = await pipeline.generate_report()

        cost = pipeline.usage.get_cost()

        audit.raw_output = response
        audit.status = AuditStatusEnum.SUCCESS

        # NOTE: could remove this if condition in the future. Free via the app.
        if not should_publish:
            # implied that it's not a FIRST_PARTY app
            if audit.app:
                user = audit.app.owner
                user.used_credits += cost
                await user.save()
            else:
                user = audit.user
                user.used_credits += cost
                await user.save()

    except Exception as err:
        logging.exception(err)
        audit.status = AuditStatusEnum.FAILED
        audit.processing_time_seconds = (datetime.now() - now).seconds
        await audit.save()
        raise err

    audit.processing_time_seconds = (datetime.now() - now).seconds
    await audit.save()

    return {"audit_id": audit_id, "audit_status": audit.status}


async def handle_outgoing_webhook(
    audit_id: str,
    audit_status: AuditStatusEnum,
    webhook_url: str,
):
    response = WebhookResponse(
        success=True,
    )

    data = {
        "id": audit_id,
        "status": audit_status,
    }

    response.result = WebhookResponseData(**data)

    async with httpx.AsyncClient() as client:
        body = response.model_dump()
        await client.post(webhook_url, json=body)


async def get_deployment_contracts(network: NetworkEnum):
    logging.info(f"RUNNING contract scan for {network}")
    web3_client = Web3Client()
    provider = web3_client.get_provider(network)

    current_block = provider.eth.get_block_number()
    logging.info(f"Network: {network} --- Current block: {current_block}")
    receipts = await provider.eth.get_block_receipts(current_block)

    logging.info(f"RECEIPTS FOUND {len(receipts)}")

    deployment_addresses = []
    for receipt in receipts:
        if not receipt["to"]:
            logs = receipt["logs"]
            if logs:
                initial_log = logs[0]
                address = initial_log["address"]
                deployment_addresses.append(address)

    logging.info(f"DEPLOYMENT ADDRESSES {deployment_addresses}")

    if not deployment_addresses:
        logging.info("no deployment addresses found")
        return

    tasks = []
    blockchain_service = BlockchainService()
    async with httpx.AsyncClient() as client:
        for address in deployment_addresses:
            tasks.append(
                asyncio.create_task(
                    blockchain_service.fetch_contract_source_code_from_explorer(
                        client, address=address, network=network
                    )
                )
            )
        results: list[dict] = await asyncio.gather(*tasks)

    logging.info(f"RESULTS {results}")

    to_create = []
    for result in results:
        if result["found"]:
            if result["has_source_code"]:
                obj = {
                    "method": ContractMethodEnum.SCAN,
                    "address": address,
                    "is_available": result["has_source_code"],
                    "network": result["network"],
                    "raw_code": result["source_code"],
                }
                to_create.append(obj)

    if to_create:
        await Contract.bulk_create(objects=to_create)
    logging.info(f"Added {len(to_create)} contracts from {network}")
