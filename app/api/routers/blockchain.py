import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.blockchain.gas import fetch_gas
from app.api.blockchain.scan import ContractService
from app.pydantic.request import ContractUploadBody
from app.utils.enums import NetworkEnum


class BlockchainRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/blockchain", tags=["blockchain"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/scan/{address}", self.scan_contract, methods=["GET"]
        )
        self.router.add_api_route(
            "/scan/{address}/{network}", self.scan_contract_on_network, methods=["GET"]
        )
        self.router.add_api_route(
            "/contract/upload",
            self.upload_contract,
            methods=["POST"],
        )
        self.router.add_api_route("/gas", self.get_gas, methods=["GET"])

    async def scan_contract(self, address: str):
        contract_service = ContractService()
        response = await contract_service.fetch_from_source(address=address)

        return JSONResponse(response, status_code=200)

    async def scan_contract_on_network(self, address: str, network: str):
        try:
            network = NetworkEnum[network.upper()]
            contract_service = ContractService()
            response = await contract_service.fetch_from_source(address=address)
            return response
        except KeyError:
            raise HTTPException(status_code=500, detail="invalid network")
        except Exception as error:
            logging.error(error)
            raise HTTPException(status_code=500, detail=str(error))

    async def upload_contract(self, data: ContractUploadBody):
        contract_service = ContractService()
        response = await contract_service.fetch_from_source(
            code=data.code, network=data.network
        )

        return JSONResponse(response, status_code=200)

    async def get_gas(self):
        return await fetch_gas()
