import asyncio
import datetime
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


class ContractService:

    def __init__(
        self,
        allow_testnet: bool = False,
    ):
        self.allow_testnet = allow_testnet

    async def __get_contract(
        self,
        code: Optional[str],
        address: Optional[str],
        network: Optional[NetworkEnum],
    ) -> Optional[Contract]:
        contract = None
        filter_obj = {}

        if address:
            filter_obj["address"] = address
            if network:
                filter_obj["network"] = network
            contract = await Contract.filter(**filter_obj).first()
        else:
            hashed_content = hashlib.sha256(code.encode()).hexdigest()
            contract = await Contract.filter(hash_code=hashed_content).first()

        return contract

    async def __get_or_create_contract(
        self,
        code: Optional[str],
        address: Optional[str],
        network: Optional[NetworkEnum],
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

        contract = await self.__get_contract(
            code=code, address=address, network=network
        )

        # More granular logic below to still scan, but not update instead of create.
        if contract:
            if contract.raw_code:
                return contract

        if not contract:
            if code:
                contract = await Contract.create(
                    method=ContractMethodEnum.UPLOAD,
                    raw_code=code,
                    hash_code=hashlib.sha256(code.encode()).hexdigest(),
                )
                return contract

        if network:
            networks_scan = [network]
        else:
            networks_scan = networks_by_type[NetworkTypeEnum.MAINNET]
            if self.allow_testnet:
                networks_scan += networks_by_type[NetworkTypeEnum.TESTNET]

        # Rather than calling these sequentially and breaking, we'll call them all.
        # For example, USDC contract on ETH mainnet is an address on BASE, so it early
        # exits without finding source code...
        tasks = []
        async with httpx.AsyncClient() as client:
            for network in networks_scan:
                tasks.append(
                    asyncio.create_task(
                        self.fetch_contract_source_code_from_explorer(
                            client, address, network
                        )
                    )
                )

            results = await asyncio.gather(*tasks)

        was_found = next(filter(lambda x: x["found"], results), None)
        if was_found is None:
            return

        with_source_code = next(filter(lambda x: x["has_source_code"], results), None)

        if with_source_code is not None:
            contract_hash = hashlib.sha256(
                with_source_code["source_code"].encode()
            ).hexdigest()
            if not contract:
                contract = Contract(
                    method=ContractMethodEnum.SCAN,
                    address=address,
                    network=with_source_code["network"],
                    raw_code=with_source_code["source_code"],
                    hash_code=contract_hash,
                )
            else:
                contract.is_available = True
                contract.raw_code = with_source_code["source_code"]
                contract.hash_code = contract_hash
                contract.network = with_source_code["network"]
        else:
            if not contract:
                contract = Contract(
                    method=ContractMethodEnum.SCAN,
                    address=address,
                    network=was_found["network"],
                    is_available=False,
                )
            else:
                contract.n_retries = contract.n_retries + 1
                contract.next_attempt = datetime.datetime.now()  # come back to this.
        await contract.save()
        return contract

    async def fetch_from_source(
        self,
        code: Optional[str] = None,
        address: Optional[str] = None,
        network: Optional[NetworkEnum] = None,
    ):
        """
        This is the entry point for getting / creating Contract instances,
        coupled with block explorer scans.

        1. Search in cache
        2. Search in DB
        3. Attempt Scan -> update / create Contract observation + cache it.
        """

        if not code and not address:
            raise ValueError("Either contract code or address must be provided")

        if address:
            KEY = f"scan|{address}"
            res = await redis_client.get(KEY)
            if res:
                data = json.loads(res)
                return data

        contract = await self.__get_or_create_contract(
            code=code, address=address, network=network
        )
        if contract:
            data = {
                "id": str(contract.id),
                "source_code": contract.raw_code,
                "network": contract.network,
                "is_available": contract.is_available,
            }
            if address:
                await redis_client.set(KEY, json.dumps(data))
            return data

        raise HTTPException(
            status_code=500, detail="unable to get or create contract source code"
        )

    async def fetch_contract_source_code_from_explorer(
        self, client: httpx.AsyncClient, address: str, network: NetworkEnum
    ) -> dict:
        platform_route = network_explorer_mapper[network]
        api_key = network_explorer_apikey_mapper[network]

        url = f"https://{platform_route}/api"
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": api_key,
        }

        logging.info(f"SCANNING {network} for address {address} at url {url}")

        try:
            response = await client.get(f"{url}?{urlencode(params)}")
            response.raise_for_status()
            data = response.json()

            result = data.get("result", [])
            if result and isinstance(result, list) and len(result) > 0:
                source_code = result[0].get("SourceCode")
                if source_code:
                    return {
                        "found": True,
                        "has_source_code": True,
                        "source_code": source_code,
                        "network": network,
                    }
            raise NoSourceCodeError()
        except NoSourceCodeError:
            return {
                "found": True,
                "has_source_code": False,
                "network": network,
            }
        except Exception:
            return {
                "found": False,
                "has_source_code": False,
                "network": network,
            }
