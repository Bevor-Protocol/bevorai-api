import hashlib
import json
import logging
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.cache import redis_client
from app.db.models import Contract
from app.utils.enums import ContractMethodEnum, NetworkEnum, NetworkTypeEnum
from app.utils.errors import NoSourceCodeError
from app.utils.mappers import (
    network_explorer_apikey_mapper,
    network_explorer_mapper,
    networks_by_type,
)

logging.basicConfig(level=logging.INFO)


async def fetch_contract_source_code_from_explorer(
    client: httpx.AsyncClient, network: NetworkEnum, address: str
) -> Optional[str]:
    platform_route = network_explorer_mapper[network]
    api_key = network_explorer_apikey_mapper[network]

    url = f"https://{platform_route}/api"
    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": api_key,
    }

    try:
        response = await client.get(f"{url}?{urlencode(params)}")
        response.raise_for_status()
        data = response.json()

        result = data.get("result", [])
        if result and isinstance(result, list) and len(result) > 0:
            source_code = result[0].get("SourceCode")
            if source_code:
                return source_code
        raise NoSourceCodeError()
    except NoSourceCodeError:
        logging.warn(
            f"Call succeeded for {address} on {network}, but no source code found"
        )
        return None
    except Exception as error:
        print(
            f"Error fetching contract source code from {network} "
            f"for address {address}: {error}"
        )
        return None


async def fetch_contract_source_code(
    address: str, network: Optional[NetworkEnum] = None
):
    if not address:
        raise HTTPException(status_code=400, detail="Address parameter is required")

    KEY = f"scan|{address}"
    res = redis_client.get(KEY)
    if res:
        data = json.loads(res)
        logging.info(f"CACHE KEY HIT {KEY}")
        return data

    contract = await get_or_create_contract(
        contract_address=address, contract_network=network
    )
    if contract:
        data = {
            "source_code": contract.contract_code,
            "network": contract.contract_network,
        }
        redis_client.set(KEY, json.dumps(data))
        return data

    raise HTTPException(
        status_code=500, detail="unable to get or create contract source code"
    )


async def get_contract(
    contract_code: Optional[str] = None,
    contract_address: Optional[str] = None,
    contract_network: Optional[NetworkEnum] = None,
) -> Optional[Contract]:
    if not contract_code and not contract_address:
        raise Exception("Must provide contract_code OR contract_address")

    contract = None
    filter_obj = {}

    if contract_address:
        filter_obj["contract_address"] = contract_address
        if contract_network:
            filter_obj["contract_network"] = contract_network
        contract = await Contract.filter(**filter_obj).first()
    else:
        hashed_content = hashlib.sha256(contract_code.encode()).hexdigest()
        contract = await Contract.filter(contract_hash=hashed_content).first()

    return contract


async def get_or_create_contract(
    contract_code: Optional[str] = None,
    contract_address: Optional[str] = None,
    contract_network: Optional[NetworkEnum] = None,
    allow_testnet: bool = False,
):
    """
    A contract's source code can be queried in many ways
    1. The source code alone was used -> via upload
    2. Only the address was provided -> via scan
    3. The address and network were provided -> via scan

    If method of SCAN was used, it's possible that the contract is not verified,
    and we aren't able to fetch the source code.

    Steps:
    - code Contract record, if available
    - if we had previously managed to fetch the source code, use it and return
    - if the network was provided, search it. Otherwise search all networks
    - if source code was found, create a new Contract record, unless we already had
        a scan for this address + network and weren't able to fetch source code,
        then update it.
    """

    contract = await get_contract(
        contract_code=contract_code,
        contract_address=contract_address,
        contract_network=contract_network,
    )

    # More granular logic below to still scan, but not update instead of create.
    if contract:
        if contract.contract_code:
            return contract

    if not contract:
        if contract_code:
            contract = await Contract.create(
                method=ContractMethodEnum.UPLOAD,
                contract_code=contract_code,
                contract_hash=hashlib.sha256(contract_code.encode()).hexdigest(),
            )
            return contract

    if contract_network:
        networks_scan = [contract_network]
    else:
        networks_scan = networks_by_type[NetworkTypeEnum.MAINNET]
        if allow_testnet:
            networks_scan += networks_by_type[NetworkTypeEnum.TESTNET]

    async with httpx.AsyncClient() as client:
        for network in networks_scan:
            # we want this to be blocking so we can early exit
            source_code = await fetch_contract_source_code_from_explorer(
                client, network, contract_address
            )
            if source_code:
                contract_hash = hashlib.sha256(source_code.encode()).hexdigest()
                if not contract:
                    contract = await Contract.create(
                        method=ContractMethodEnum.SCAN,
                        contract_address=contract_address,
                        contract_network=network,
                        contract_code=source_code,
                        contract_hash=contract_hash,
                    )
                else:
                    # We might override the network here, which is fine.
                    contract.is_available = True
                    contract.contract_code = source_code
                    contract.contract_hash = contract_hash
                    contract.contract_network = network
                    await contract.save()
                return contract

    return
