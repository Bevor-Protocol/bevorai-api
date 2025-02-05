import os

from web3 import Web3

from app.utils.enums import NetworkEnum
from app.utils.mappers import network_rpc_mapper


def get_provider(network: NetworkEnum) -> Web3:
    rpc_url = network_rpc_mapper[network]
    api_key = os.getenv("ALCHEMY_API_KEY")
    url = f"https://{rpc_url}/v2/{api_key}"

    return Web3(Web3.HTTPProvider(url))
