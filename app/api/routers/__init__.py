from app.api.routers.auth import AuthRouter

from .ai import AiRouter
from .blockchain import BlockchainRouter
from .health import BaseRouter
from .status import StatusRouter
from .websocket import WebsocketRouter

base_router = BaseRouter().router
ai_router = AiRouter().router
blockchain_router = BlockchainRouter().router
status_router = StatusRouter().router
websocket_router = WebsocketRouter().router
auth_router = AuthRouter().router
