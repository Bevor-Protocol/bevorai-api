import asyncio
from datetime import datetime

import httpx
import logfire

from app.api.blockchain.service import BlockchainService
from app.db.models import Audit, Auth, Contract, Transaction
from app.lib.clients import Web3Client
from app.utils.types.enums import (
    AppTypeEnum,
    AuditStatusEnum,
    ClientTypeEnum,
    ContractMethodEnum,
    NetworkEnum,
    TransactionTypeEnum,
)

from .pipelines.audit_generation import LlmPipeline


async def handle_eval(audit_id: str):
    now = datetime.now()
    audit = await Audit.get(id=audit_id).select_related("contract")

    if audit.app_id:
        caller_auth = await Auth.get(app_id=audit.app_id).select_related("app__owner")
    else:
        caller_auth = await Auth.get(user_id=audit.user_id).select_related("user")

    pipeline = LlmPipeline(
        audit=audit,
        should_publish=False,
    )

    audit.status = AuditStatusEnum.PROCESSING
    await audit.save()

    try:
        await pipeline.generate_candidates()
        result = await pipeline.generate_report()

        await pipeline.write_results(
            response=result,
            status=AuditStatusEnum.SUCCESS,
            processing_time_seconds=(datetime.now() - now).seconds,
        )
    except Exception as err:
        logfire.exception(str(err), **{"audit_id": str(audit.id)})
        await pipeline.write_results(
            response=None,
            status=AuditStatusEnum.FAILED,
            processing_time_seconds=(datetime.now() - now).seconds,
        )
        raise err

    # NOTE: could remove this if condition in the future. Free via the app.

    cost = pipeline.usage.get_cost()

    transaction = Transaction(
        app_id=audit.app_id,
        user_id=audit.user_id,
        type=TransactionTypeEnum.SPEND,
        amount=cost,
    )

    if caller_auth.consumes_credits:
        if caller_auth.client_type == ClientTypeEnum.APP:
            app = caller_auth.app
            if app.type == AppTypeEnum.THIRD_PARTY:
                user = caller_auth.app.owner
                user.used_credits += cost

                logfire.info(
                    "spending credits for audit as app",
                    **{
                        "audit_id": str(audit.id),
                        "cost": cost,
                        "user_id": str(user.id),
                    },
                )

                await user.save()
                await transaction.save()
        else:
            user = caller_auth.user
            user.used_credits += cost

            logfire.info(
                "spending credits for audit as user",
                **{
                    "audit_id": str(audit.id),
                    "cost": cost,
                    "user_id": str(user.id),
                },
            )

            await user.save()
            await transaction.save()

    return {"audit_id": audit_id, "audit_status": audit.status}


async def get_deployment_contracts(network: NetworkEnum):
    logfire.info(f"RUNNING contract scan for {network}")
    web3_client = Web3Client()
    current_block = await web3_client.get_block_number()
    logfire.info(f"Network: {network} --- Current block: {current_block}")
    receipts = await web3_client.get_block_receipts(current_block)

    logfire.info(f"RECEIPTS FOUND {len(receipts)}")

    deployment_addresses = []
    for receipt in receipts:
        if not receipt["to"]:
            logs = receipt["logs"]
            if logs:
                initial_log = logs[0]
                address = initial_log["address"]
                deployment_addresses.append(address)

    logfire.info(f"DEPLOYMENT ADDRESSES {deployment_addresses}")

    if not deployment_addresses:
        logfire.info("no deployment addresses found")
        return

    tasks = []
    blockchain_service = BlockchainService()
    async with httpx.AsyncClient() as client:
        for address in deployment_addresses:
            tasks.append(
                asyncio.create_task(
                    blockchain_service.get_source_code(
                        client, address=address, network=network
                    )
                )
            )
        results: list[dict] = await asyncio.gather(*tasks)

    logfire.info(f"RESULTS {results}")

    to_create = []
    for result in results:
        if result["found"]:
            if result["has_source_code"]:
                obj = {
                    "method": ContractMethodEnum.SCAN,
                    "address": address,
                    "is_available": result["has_source_code"],
                    "network": result["network"],
                    "code": result["source_code"],
                }
                to_create.append(obj)

    if to_create:
        await Contract.bulk_create(objects=to_create)
    logfire.info(f"Added {len(to_create)} contracts from {network}")
