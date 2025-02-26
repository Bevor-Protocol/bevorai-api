from fastapi import APIRouter, Depends

from app.api.blockchain.service import BlockchainService
from app.api.dependencies import Authentication
from app.utils.types.enums import RoleEnum


class BlockchainRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/blockchain", include_in_schema=False)
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/gas",
            self.get_gas,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
        )

    async def get_gas(self):
        blockchain_service = BlockchainService()
        return await blockchain_service.get_gas()
