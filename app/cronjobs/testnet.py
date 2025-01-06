import logging
from typing import List
from urllib.parse import urlencode

import httpx

from app.api.blockchain.scan import fetch_contract_source_code_from_explorer
from app.utils.enums import NetworkEnum, NetworkTypeEnum
from app.utils.mappers import (
    network_explorer_apikey_mapper,
    network_rpc_mapper,
    networks_by_type,
)


async def fetch_recent_contracts_with_verified_source(
    network: NetworkEnum,
) -> List[str]:
    route = network_rpc_mapper[network]
    api_key = network_explorer_apikey_mapper[network]

    url = f"https://api.{route}/api"
    params = {
        "module": "contract",
        "action": "getrecentverifiedcontracts",
        "apikey": api_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}?{urlencode(params)}")
            response.raise_for_status()
            data = response.json()

            contracts = data.get("result", [])
            return [
                contract.get("address")
                for contract in contracts
                if contract.get("address")
            ]

    except Exception as error:
        print(f"Error fetching recent contracts from {network}: {error}")
        return []


async def scan_testnets_for_verified_contracts():
    networks = networks_by_type[NetworkTypeEnum.TESTNET]

    tasks = []
    async with httpx.AsyncClient() as client:
        for network in networks:
            logging.info(f"Scanning {network}")
            tasks.append(fetch_recent_contracts_with_verified_source(network))
            contracts = await fetch_recent_contracts_with_verified_source(network)
            for address in contracts:
                source_code = await fetch_contract_source_code_from_explorer(
                    client, network, address
                )
                if source_code:
                    print(f"Verified contract found on {network}: {address}")
                    # Process the source code as needed
