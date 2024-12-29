import os
from typing import Optional, List
from urllib.parse import urlencode
import httpx

async def get_api_key_for_platform(platform: str) -> Optional[str]:
    platform_key_map = {
        "etherscan.io": "ETHERSCAN_API_KEY",
        "bscscan.com": "BSCSCAN_API_KEY",
        "polygonscan.com": "POLYGONSCAN_API_KEY",
        "basescan.org": "BASESCAN_API_KEY",
    }
    return os.getenv(platform_key_map.get(platform, ""))

async def fetch_recent_contracts_with_verified_source(platform: str) -> List[str]:
    api_key = await get_api_key_for_platform(platform)
    if not api_key:
        print(f"No API key found for platform: {platform}")
        return []

    url = f"https://api.{platform}/api"
    params = {
        "module": "contract",
        "action": "getrecentverifiedcontracts",
        "apikey": api_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}?{urlencode(params)}")
            response.raise_for_status()
            data = response.json()

            contracts = data.get("result", [])
            return [contract.get("address") for contract in contracts if contract.get("address")]

    except Exception as error:
        print(f"Error fetching recent contracts from {platform}: {error}")
        return []

async def scan_testnets_for_verified_contracts():
    platforms = ["etherscan.io", "bscscan.com", "polygonscan.com", "basescan.org"]
    async with httpx.AsyncClient() as client:
        for platform in platforms:
            print(f"Scanning {platform} for verified contracts...")
            contracts = await fetch_recent_contracts_with_verified_source(platform)
            for address in contracts:
                source_code = await fetch_contract_source_code_from_explorer(client, platform, address)
                if source_code:
                    print(f"Verified contract found on {platform}: {address}")
                    # Process the source code as needed
