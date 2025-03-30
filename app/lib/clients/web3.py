import os

from eth_typing import BlockNumber
from web3 import AsyncWeb3
from web3.types import BlockReceipts

from app.utils.constants.mappers import network_rpc_mapper
from app.utils.logger import get_logger
from app.utils.types.enums import NetworkEnum

logger = get_logger("api")


class Web3Client:

    def __init__(self, network: NetworkEnum):
        self.provider = self._get_provider(network=network)
        self.ENV = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")

    @classmethod
    def from_deployment(cls):
        instance = cls._new_(cls)
        instance.provider = instance.get_deployed_provider()
        return instance

    def _get_base_url(self, network: NetworkEnum) -> str:
        rpc_url = network_rpc_mapper[network]
        api_key = os.getenv("ALCHEMY_API_KEY")
        url = f"https://{rpc_url}/v2/{api_key}"

        return url

    def _get_provider(self, network: NetworkEnum) -> AsyncWeb3:
        url = self._get_base_url(network)

        return AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(url))

    def get_deployed_provider(self) -> AsyncWeb3:
        url_mappper = {
            "production": self._get_base_url(NetworkEnum.BASE),
            "staging": self._get_base_url(NetworkEnum.ETH_SEPOLIA),
            "development": os.getenv("LOCAL_BLOCKCHAIN_URL"),
        }

        url = url_mappper[self.ENV]

        return AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(url))

    async def get_block_number(self) -> BlockNumber:
        block = await self.provider.eth.get_block_number()
        return block

    async def get_block_receipts(self, block: BlockNumber) -> BlockReceipts:
        receipts = await self.provider.eth.get_block_receipts(block)
        return receipts

    async def get_user_credits(self, user_address: str) -> int:

        contract_mapper = {
            "production": "0x1bdEEe6376572F1CAE454dC68a936Af56A803e96",
            "staging": "0xbc14A36c59154971A8Eb431031729Af39f97eEd1",
            "development": "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
        }

        abi = [
            {
                "inputs": [{"type": "address"}],
                "name": "apiCredits",
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            }
        ]

        contract_address = self.provider.to_checksum_address(contract_mapper[self.ENV])
        user_addres = self.provider.to_checksum_address(user_address)

        try:
            contract = self.provider.eth.contract(address=contract_address, abi=abi)
            raw_credits = await contract.functions.apiCredits(user_addres).call()
            credits = raw_credits / 10**18
            return credits
        except Exception:
            # most likely in development, if not running anvil + connected to ngrok
            logger.warning("unable to query contract")
            return 0
