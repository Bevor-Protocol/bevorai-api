import logging
import os

import httpx

from app.utils.clients.explorer import ExplorerClient
from app.utils.clients.web3 import Web3Client
from app.utils.helpers.code_parser import SourceCodeParser
from app.utils.types.enums import NetworkEnum


class BlockchainService:

    async def get_gas(self) -> dict:
        explorer_client = ExplorerClient()

        async with httpx.AsyncClient() as client:
            response = await explorer_client.get_gas(
                client=client, network=NetworkEnum.ETH
            )
            response.raise_for_status()

            data = response.json()
            return data

    async def get_source_code(
        self, client: httpx.AsyncClient, address: str, network: NetworkEnum
    ) -> dict:
        explorer_client = ExplorerClient()

        logging.info(f"SCANNING {network} for address {address}")

        obj = {
            "network": network,
            "address": address,
            "exists": False,
            "is_available": False,
            "code": None,
            "is_proxy": False,
            "contract_name": None,
        }

        try:
            response = await explorer_client.get_source_code(
                client=client, network=network, address=address
            )
            response.raise_for_status()
            data = response.json()

            result = data.get("result")
            if result and isinstance(result, list) and len(result) > 0:
                obj["exists"] = True
                parser = SourceCodeParser(result[0])
                parser.extract_raw_code()
                obj["is_available"] = parser.source != ""
                obj["code"] = parser.source if parser.source != "" else None
                obj["contract_name"] = parser.contract_name
                obj["is_proxy"] = parser.is_proxy
        except Exception as err:
            logging.exception(err)
        finally:
            return obj

    async def get_credits(self, address: str) -> float:
        """
        Call the apiCredit contract directly.
        """
        web3_client = Web3Client()
        provider = web3_client.get_deployed_provider()

        env = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
        if env == "production":
            # mainnet BASE contract
            contract_address = provider.to_checksum_address(
                "0x1bdEEe6376572F1CAE454dC68a936Af56A803e96"
            )
        elif env == "staging":
            # testnet Sepolia contract
            contract_address = provider.to_checksum_address(
                "0xbc14A36c59154971A8Eb431031729Af39f97eEd1"
            )
        else:
            # local anvil deployment
            contract_address = provider.to_checksum_address(
                "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512"
            )

        user_address = provider.to_checksum_address(address)

        abi = [
            {
                "inputs": [{"type": "address"}],
                "name": "apiCredits",
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            }
        ]

        contract = provider.eth.contract(address=contract_address, abi=abi)

        # Call apiCredits mapping to get credits for the address
        credits_raw = await contract.functions.apiCredits(user_address).call()
        credits = credits_raw / 10**18

        return credits
