import asyncio
import hashlib
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
        results = await asyncio.gather(*tasks)

    logging.info(f"RESULTS {results}")

    to_create = []
    n_available = 0
    n_unavailable = 0
    for i, address in enumerate(deployment_addresses):
        result = results[i]
        has_source_code = result["has_source_code"]
        found = result["found"]
        if found:
            source_code = None
            hashed = None
            if has_source_code:
                n_available += 1
                source_code = result["source_code"]
                hashed = hashlib.sha256(source_code.encode()).hexdigest()
            else:
                n_unavailable += 1

            to_create.append(
                Contract(
                    method=ContractMethodEnum.CRON,
                    contract_address=address,
                    contract_network=network,
                    contract_code=source_code,
                    contract_hash=hashed,
                    is_available=has_source_code,
                )
            )

    await Contract.bulk_create(objects=to_create)
    logging.info(
        f"Added {len(to_create)} contracts from {network}"
        f" --- {n_available} available source code"
        f" --- {n_unavailable} not available source code"
    )
