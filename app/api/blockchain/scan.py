import asyncio
import hashlib
import logging
from typing import List, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

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

    async def __get_contract_candidates(
        self,
        code: Optional[str],
        address: Optional[str],
        network: Optional[NetworkEnum],
    ) -> List[Contract]:
        filter_obj = {"is_available": True, "raw_code__isnull": False}

        if address:
            filter_obj["address"] = address
            if network:
                filter_obj["network"] = network
            contracts = await Contract.filter(**filter_obj)
        else:
            hashed_content = hashlib.sha256(code.encode()).hexdigest()
            filter_obj["hash_code"] = hashed_content
            if network:
                filter_obj["network"] = network
            contracts = await Contract.filter(hash_code=hashed_content)

        return contracts or []

    async def __get_or_create_contract(
        self,
        code: Optional[str],
        address: Optional[str],
        network: Optional[NetworkEnum],
    ) -> List[Contract]:
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

        contracts = await self.__get_contract_candidates(
            code=code, address=address, network=network
        )

        # More granular logic below to still scan, but not update instead of create.
        if contracts:
            return contracts

        if code:
            contract = await Contract.create(
                method=ContractMethodEnum.UPLOAD,
                network=network,
                raw_code=code,
            )
            return [contract]

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
                            client=client, address=address, network=network
                        )
                    )
                )

            results: list[dict] = await asyncio.gather(*tasks)

        to_create: list[dict] = []
        for result in results:
            if result["found"]:
                obj = {
                    "method": ContractMethodEnum.SCAN,
                    "address": address,
                    "is_available": result["has_source_code"],
                    "network": result["network"],
                }
                if result["has_source_code"]:
                    obj["raw_code"] = result["source_code"]
                to_create.append(obj)

                # contract.n_retries = contract.n_retries + 1
                # contract.next_attempt = datetime.datetime.now()

        if to_create:
            contracts = []
            # bulk_create doesn't return.
            for obj in to_create:
                contract_created = await Contract.create(**obj)
                if obj["is_available"]:
                    contracts.append(contract_created)
            # contracts = await Contract.bulk_create(objects=to_create)

        return contracts

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

        contracts = await self.__get_or_create_contract(
            code=code, address=address, network=network
        )

        if not contracts:
            raise HTTPException(
                status_code=500, detail="unable to get or create contract source code"
            )

        def prettify(contract: Contract):
            return {
                "id": str(contract.id),
                "source_code": contract.raw_code,
                "network": contract.network,
                "is_available": contract.is_available,
            }

        obj = {
            "exact_match": len(contracts) == 1,
            "exists": bool(len(contracts)),
            "candidates": list(map(prettify, contracts)),
        }

        return obj

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

        obj = {
            "network": network,
            "address": address,
            "has_source_code": False,
            "found": False,
            "source_code": None,
        }

        try:
            response = await client.get(f"{url}?{urlencode(params)}")
            response.raise_for_status()
            data = response.json()

            result = data.get("result")
            if result and isinstance(result, list) and len(result) > 0:
                obj["found"] = True
                source_code = result[0].get("SourceCode")
                if source_code:
                    obj["has_source_code"] = True
                    obj["source_code"] = source_code
            raise NoSourceCodeError()
        except NoSourceCodeError:
            obj["found"] = True
        except Exception:
            pass
        finally:
            return obj
