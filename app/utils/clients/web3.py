import os

from web3 import AsyncWeb3

from app.utils.helpers.mappers import network_rpc_mapper
from app.utils.types.enums import NetworkEnum


class Web3Client:

    def __get_base_url(self, network: NetworkEnum) -> str:
        rpc_url = network_rpc_mapper[network]
        api_key = os.getenv("ALCHEMY_API_KEY")
        url = f"https://{rpc_url}/v2/{api_key}"

        return url

    def get_provider(self, network: NetworkEnum) -> AsyncWeb3:
        url = self.__get_base_url(network)

        return AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(url))

    def get_deployed_provider(self) -> AsyncWeb3:
        env = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
        if env == "production":
            url = self.__get_base_url(NetworkEnum.BASE)
        elif env == "staging":
            url = self.__get_base_url(NetworkEnum.BASE_SEPOLIA)
        else:
            # url = "http://127.0.0.1:8545"
            url = "https://accurate-joey-master.ngrok-free.app"

        return AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(url))
