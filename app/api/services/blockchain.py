import logging

import httpx

from app.client.explorer import ExplorerClient
from app.utils.enums import NetworkEnum
from app.utils.errors import NoSourceCodeError


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

    async def fetch_contract_source_code_from_explorer(
        self, client: httpx.AsyncClient, address: str, network: NetworkEnum
    ) -> dict:
        explorer_client = ExplorerClient()

        logging.info(f"SCANNING {network} for address {address}")

        obj = {
            "network": network,
            "address": address,
            "has_source_code": False,
            "found": False,
            "source_code": None,
        }

        try:
            response = await explorer_client.get_source_code(
                client=client, network=network, address=address
            )
            response.raise_for_status()
            data = response.json()

            result = data.get("result")
            if result and isinstance(result, list) and len(result) > 0:
                obj["found"] = True
                source_code = result[0].get("SourceCode")
                if source_code:
                    obj["has_source_code"] = True
                    obj["source_code"] = source_code
            raise NoSourceCodeError()
        except NoSourceCodeError:
            obj["found"] = True
        except Exception:
            pass
        finally:
            return obj
