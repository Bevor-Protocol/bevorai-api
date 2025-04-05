import httpx

from app.lib.clients import ExplorerClient, Web3Client
from app.utils.helpers.code_parser import SourceCodeParser
from app.utils.logger import get_logger
from app.utils.types.enums import NetworkEnum

logger = get_logger("api")


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

        logger.info(f"SCANNING {network} for address {address}")

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
                parser.extract_code()
                obj["is_available"] = parser.source != ""
                obj["code"] = parser.source if parser.source != "" else None
                obj["contract_name"] = parser.contract_name
                obj["is_proxy"] = parser.is_proxy
        except Exception as err:
            logger.exception(err)
        finally:
            return obj

    async def get_credits(self, address: str) -> float:
        """
        Call the apiCredit contract directly.
        """
        web3_client = Web3Client.from_deployment()

        credits = await web3_client.get_user_credits(user_address=address)
        return credits
