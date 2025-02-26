from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from tortoise.exceptions import DoesNotExist

from app.api.contract.service import ContractService
from app.api.dependencies import AuthenticationWithoutDelegation, RequireCredits
from app.api.pricing.service import StaticAnalysis
from app.db.models import User
from app.utils.constants.openapi_tags import CONTRACT_TAG
from app.utils.schema.dependencies import AuthState
from app.utils.schema.request import ContractScanBody
from app.utils.types.enums import AuthRequestScopeEnum, AuthScopeEnum

from .openapi import ANALYZE_TOKEN, GET_CONTRACT, GET_OR_CREATE_CONTRACT


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
            **GET_OR_CREATE_CONTRACT,
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
            **GET_CONTRACT,
        )
        self.router.add_api_route(
            "/token/static",
            self.process_token,
            methods=["POST"],
            dependencies=[
                Depends(
                    AuthenticationWithoutDelegation(
                        request_scope=AuthRequestScopeEnum.USER
                    )
                ),
                Depends(RequireCredits()),
            ],
            **ANALYZE_TOKEN,
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

    async def process_token(
        self,
        request: Request,
        body: Annotated[ContractScanBody, Body()],
    ):
        contract_service = ContractService()
        static_pricing = StaticAnalysis()
        auth: AuthState = request.state.auth
        consume_credits = (not auth.app_id) or (auth.scope != AuthScopeEnum.ADMIN)

        response = await contract_service.process_static_eval_token(body)

        if consume_credits:
            user = await User.get(id=auth.credit_consumer_id)
            price = static_pricing.get_cost()
            user.used_credits += price
            await user.save()

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
