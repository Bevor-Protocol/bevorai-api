from .app import AppRouter
from .audit import AuditRouter
from .auth import AuthRouter
from .base import BaseRouter
from .blockchain import BlockchainRouter
from .contract import ContractRouter
from .platform import PlatformRouter
from .user import UserRouter
from .websocket import WebsocketRouter
from .static import StaticRouter

app_router = AppRouter().router
audit_router = AuditRouter().router
auth_router = AuthRouter().router
base_router = BaseRouter().router
blockchain_router = BlockchainRouter().router
contract_router = ContractRouter().router
platform_router = PlatformRouter().router
user_router = UserRouter().router
websocket_router = WebsocketRouter().router
static_router = StaticRouter().router
