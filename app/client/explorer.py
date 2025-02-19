from urllib.parse import urlencode

import httpx

from app.utils.enums import NetworkEnum, NetworkTypeEnum
from app.utils.mappers import (
    network_chainid_mapper,
    network_explorer_apikey_mapper,
    network_explorer_mapper,
    networks_by_type,
)


class ExplorerClient:

    def __get_base_url(self, network: NetworkEnum) -> str:
        platform_route = network_explorer_mapper[network]
        chain_id = network_chainid_mapper[network]

        url = f"https://{platform_route}"

        if platform_route == "api.routescan.io":
            is_testnet = network in networks_by_type[NetworkTypeEnum.TESTNET]
            network_type = "testnet" if is_testnet else "mainnet"
            url += f"/v2/network/{network_type}/evm/{chain_id}/etherscan/api"
        else:
            url += "/api"

        return url

    async def get_source_code(
        self, client: httpx.AsyncClient, network: NetworkEnum, address: str
    ) -> httpx.Response:
        api_key = network_explorer_apikey_mapper[network]

        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": api_key,
        }

        url = self.__get_base_url(network=network)
        params_encoded = urlencode(params)

        return await client.get(f"{url}?{params_encoded}")

    async def get_gas(
        self, client: httpx.AsyncClient, network: NetworkEnum
    ) -> httpx.Response:
        api_key = network_explorer_apikey_mapper[network]

        params = {
            "module": "gastracker",
            "action": "gasoracle",
            "apikey": api_key,
        }

        url = self.__get_base_url(network=network)
        params_encoded = urlencode(params)

        return await client.get(f"{url}?${params_encoded}")
