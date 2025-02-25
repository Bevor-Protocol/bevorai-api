import asyncio
import hashlib
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.api.services.blockchain import BlockchainService
from app.db.models import Contract
from app.utils.helpers.mappers import networks_by_type
from app.utils.helpers.model_parser import cast_contract_with_code
from app.utils.schema.contract import ContractWithCodePydantic
from app.utils.schema.response import UploadContractResponse
from app.utils.types.enums import ContractMethodEnum, NetworkEnum, NetworkTypeEnum


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
    ) -> list[Contract]:
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
    ) -> list[Contract]:
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
        blockchain_service = BlockchainService()
        async with httpx.AsyncClient() as client:
            for network in networks_scan:
                tasks.append(
                    asyncio.create_task(
                        blockchain_service.fetch_contract_source_code_from_explorer(
                            client=client, address=address, network=network
                        )
                    )
                )

            results: list[dict] = await asyncio.gather(*tasks)

        # only return those with source code.
        contracts_return: list[Contract] = []
        for result in results:
            if result["found"]:
                contract = Contract(
                    method=ContractMethodEnum.SCAN,
                    address=address,
                    is_available=result["has_source_code"],
                    network=result["network"],
                )
                if result["has_source_code"]:
                    contract.raw_code = result["source_code"]
                    await contract.save()
                    contracts_return.append(contract)
                else:
                    await contract.save()

                # contract.n_retries = contract.n_retries + 1
                # contract.next_attempt = datetime.datetime.now()

        return contracts_return

    async def fetch_from_source(
        self,
        code: Optional[str] = None,
        address: Optional[str] = None,
        network: Optional[NetworkEnum] = None,
    ) -> UploadContractResponse:

        if not code and not address:
            raise ValueError("Either contract code or address must be provided")

        contracts = await self.__get_or_create_contract(
            code=code, address=address, network=network
        )

        if not contracts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="unable to get or create contract source code",
            )

        first_candidate = next(filter(lambda x: x.is_available, contracts), None)

        return UploadContractResponse(
            exact_match=len(contracts) == 1,
            exists=bool(len(contracts)),
            contract=first_candidate,
        )

    async def get(self, id: str) -> ContractWithCodePydantic:

        contract = await Contract.get(id=id)

        return cast_contract_with_code(contract)
