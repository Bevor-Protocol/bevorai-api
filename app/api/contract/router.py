from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from tortoise.exceptions import DoesNotExist

from app.api.core.dependencies import AuthenticationWithoutDelegation
from app.api.services.contract import ContractService
from app.utils.constants.openapi_tags import CONTRACT_TAG
from app.utils.openapi import OPENAPI_SPEC
from app.utils.schema.request import ContractScanBody
from app.utils.types.enums import AuthRequestScopeEnum


class ContractRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/contract", tags=[CONTRACT_TAG])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "",
            self.upload_contract,
            methods=["POST"],
            dependencies=[
                Depends(
                    AuthenticationWithoutDelegation(
                        request_scope=AuthRequestScopeEnum.USER
                    )
                )
            ],
            **OPENAPI_SPEC["get_or_create_contract"],
        )
        self.router.add_api_route(
            "/{id}",
            self.get_contract,
            methods=["GET"],
            dependencies=[
                Depends(
                    AuthenticationWithoutDelegation(
                        request_scope=AuthRequestScopeEnum.USER
                    )
                )
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

        try:
            response = await contract_service.get(id)
            return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this contract does not exist",
            )
