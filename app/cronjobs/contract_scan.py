import asyncio
import logging

import httpx

from app.api.blockchain.scan import ContractService
from app.api.web3.provider import get_provider
from app.db.models import Contract
from app.utils.enums import ContractMethodEnum, NetworkEnum


async def get_deployment_contracts(network: NetworkEnum):
    logging.info(f"RUNNING contract scan for {network}")
    provider = get_provider(network)

    current_block = provider.eth.get_block_number()
    logging.info(f"Network: {network} --- Current block: {current_block}")
    receipts = provider.eth.get_block_receipts(current_block)

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
    contract_service = ContractService()
    async with httpx.AsyncClient() as client:
        for address in deployment_addresses:
            tasks.append(
                asyncio.create_task(
                    contract_service.fetch_contract_source_code_from_explorer(
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
