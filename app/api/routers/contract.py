from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response, status

from app.api.core.dependencies import Authentication
from app.api.services.contract import ContractService
from app.schema.request import ContractScanBody
from app.utils.enums import AuthRequestScopeEnum
from app.utils.openapi import OPENAPI_SPEC


class ContractRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/contract", tags=["contract"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/",
            self.upload_contract,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_or_create_contract"],
        )
        self.router.add_api_route(
            "/{id}",
            self.get_contract,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_contract"],
        )

    async def upload_contract(self, body: Annotated[ContractScanBody, Body()]):
        contract_service = ContractService()
        response = await contract_service.fetch_from_source(
            address=body.address, network=body.network, code=body.code
        )

        return Response(
            response.model_dump_json(), status_code=status.HTTP_202_ACCEPTED
        )

    async def get_contract(self, id: str):
        contract_service = ContractService()

        response = await contract_service.get_contract(id)

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
