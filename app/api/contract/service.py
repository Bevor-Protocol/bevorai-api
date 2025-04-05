import asyncio
import hashlib
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.api.blockchain.service import BlockchainService
from app.db.models import Contract
from app.utils.helpers.code_parser import SourceCodeParser
from app.utils.logger import get_logger
from app.utils.mappers import networks_by_type
from app.utils.types.models import ContractSchema
from app.utils.types.enums import ContractMethodEnum, NetworkEnum, NetworkTypeEnum

from .interface import (
    ContractScanBody,
    StaticAnalysisTokenResult,
    UploadContractResponse,
)

logger = get_logger("api")


class ContractService:
    def __init__(
        self,
        allow_testnet: bool = False,
    ):
        self.allow_testnet = allow_testnet

    async def _get_or_create_contract(
        self,
        code: Optional[str],
        address: Optional[str],
        network: Optional[NetworkEnum],
    ) -> list[Contract]:
        """
        If contract was previously uploaded / fetched, return it.
        Otherwise get from source
        """

        filter_obj = {"is_available": True, "raw_code__isnull": False}

        if address:
            filter_obj["address"] = address
        if network:
            filter_obj["network"] = network
        if code:
            hashed_content = hashlib.sha256(code.encode()).hexdigest()
            filter_obj["hash_code"] = hashed_content

        contracts = await Contract.filter(**filter_obj)

        if contracts:
            logger.info(f"early exiting for {address}")
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
                        blockchain_service.get_source_code(
                            client=client, address=address, network=network
                        )
                    )
                )

            results: list[dict] = await asyncio.gather(*tasks)

        # only return those with source code.
        contracts_return: list[Contract] = []
        for result in results:
            if result["exists"]:
                contract = await Contract.create(
                    method=ContractMethodEnum.SCAN,
                    address=address,
                    is_available=result["is_available"],
                    network=result["network"],
                    is_proxy=result["is_proxy"],
                    contract_name=result["contract_name"],
                    raw_code=result["code"],
                )
                if contract.is_available:
                    contracts_return.append(contract)

        return contracts_return

    async def fetch_from_source(
        self,
        code: Optional[str] = None,
        address: Optional[str] = None,
        network: Optional[NetworkEnum] = None,
    ) -> UploadContractResponse:
        if not code and not address:
            raise ValueError("Either contract code or address must be provided")

        contracts = await self._get_or_create_contract(
            code=code, address=address, network=network
        )

        first_candidate = next(filter(lambda x: x.is_available, contracts), None)
        if first_candidate:
            first_candidate = ContractSchema.from_tortoise(first_candidate)

        return UploadContractResponse(
            exact_match=len(contracts) == 1,
            exists=first_candidate is not None,
            contract=first_candidate,
        )

    async def get(self, id: str) -> Contract:
        contract = await Contract.get(id=id)

        return contract

    async def process_static_eval_token(
        self, body: ContractScanBody
    ) -> StaticAnalysisTokenResult:
        contracts = await self._get_or_create_contract(
            code=body.code, address=body.address, network=body.network
        )

        first_candidate = next(filter(lambda x: x.is_available, contracts), None)
        if not first_candidate:
            raise HTTPException(
                detail="no source code found for this address",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if not first_candidate.is_parsable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unable to parse smart contract code",
            )

        parser = SourceCodeParser.from_contract_instance(first_candidate)
        parser.generate_ast()
        analysis = parser.analyze_contract()

        return analysis
