from .admin.router import AdminRouter
from .app.router import AppRouter
from .audit.router import AuditRouter
from .auth.router import AuthRouter
from .base.router import BaseRouter
from .blockchain.router import BlockchainRouter
from .contract.router import ContractRouter
from .platform.router import PlatformRouter
from .user.router import UserRouter
from .websocket.router import WebsocketRouter

admin_router = AdminRouter().router
app_router = AppRouter().router
audit_router = AuditRouter().router
auth_router = AuthRouter().router
base_router = BaseRouter().router
blockchain_router = BlockchainRouter().router
contract_router = ContractRouter().router
platform_router = PlatformRouter().router
user_router = UserRouter().router
websocket_router = WebsocketRouter().router
