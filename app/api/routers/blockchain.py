from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response, status

from app.api.core.dependencies import Authentication
from app.api.services.blockchain import BlockchainService
from app.api.services.contract import ContractService
from app.schema.request import ContractScanBody
from app.utils.enums import AuthRequestScopeEnum
from app.utils.openapi import OPENAPI_SPEC


class BlockchainRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/blockchain", tags=["blockchain"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/contract",
            self.upload_contract,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["upsert_contract"],
        )
        self.router.add_api_route(
            "/gas",
            self.get_gas,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            include_in_schema=False,
        )

    async def upload_contract(self, body: Annotated[ContractScanBody, Body()]):
        contract_service = ContractService()
        response = await contract_service.fetch_from_source(
            address=body.address, network=body.network, code=body.code
        )

        return Response(
            response.model_dump_json(), status_code=status.HTTP_202_ACCEPTED
        )

    async def get_gas(self):
        blockchain_service = BlockchainService()
        return await blockchain_service.get_gas()
