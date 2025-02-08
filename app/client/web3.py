import os

from web3 import Web3

from app.utils.enums import NetworkEnum
from app.utils.mappers import network_rpc_mapper


class Web3Client:

    def __get_base_url(self, network: NetworkEnum) -> str:
        rpc_url = network_rpc_mapper[network]
        api_key = os.getenv("ALCHEMY_API_KEY")
        url = f"https://{rpc_url}/v2/{api_key}"

        return url

    def get_provider(self, network: NetworkEnum) -> Web3:
        url = self.__get_base_url(network)

        return Web3(Web3.HTTPProvider(url))
