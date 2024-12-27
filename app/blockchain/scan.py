import os
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException


def get_api_key_for_platform(platform: str) -> Optional[str]:
    platform_keys = {
        "etherscan.io": os.getenv("ETHERSCAN_API_KEY"),
        "api-sepolia.etherscan.io": os.getenv("ETHERSCAN_API_KEY"),
        "bscscan.com": os.getenv("BSCSCAN_API_KEY"),
        "api-testnet.bscscan.com": os.getenv("BSCSCAN_API_KEY"),
        "polygonscan.com": os.getenv("POLYGONSCAN_API_KEY"),
        "api-amoy.polygonscan.com": os.getenv("POLYGONSCAN_API_KEY"),
        "basescan.org": os.getenv("BASESCAN_API_KEY"),
        "api-sepolia.basescan.org": os.getenv("BASESCAN_API_KEY"),
    }
    return platform_keys.get(platform)


async def fetch_contract_source_code_from_explorer(
    client: httpx.AsyncClient, platform: str, address: str
) -> Optional[str]:
    try:
        api_key = get_api_key_for_platform(platform)
        if not api_key:
            print(f"No API key found for platform: {platform}")
            return

        url = f"https://api.{platform}/api"
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": api_key,
        }

        response = await client.get(f"{url}?{urlencode(params)}")
        response.raise_for_status()
        data = response.json()

        result = data.get("result", [])
        if result and isinstance(result, list) and len(result) > 0:
            source_code = result[0].get("SourceCode")
            if source_code:
                return source_code

        print(f"No source code found for contract {address} on {platform}")

    except Exception as error:
        print(
            f"Error fetching contract source code from {platform} "
            f"for address {address}: {error}"
        )
        return None


async def fetch_contract_source_code(address: str):
    try:
        platforms = ["etherscan.io", "bscscan.com", "polygonscan.com", "basescan.org"]

        if not address:
            raise HTTPException(status_code=400, detail="Address parameter is required")

        async with httpx.AsyncClient() as client:
            for platform in platforms:
                source_code = await fetch_contract_source_code_from_explorer(
                    client, platform, address
                )
                if source_code:
                    return {"platform": platform, "source_code": source_code}

        raise HTTPException(
            status_code=404,
            detail="No source code found for the given address on any platform",
        )

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
