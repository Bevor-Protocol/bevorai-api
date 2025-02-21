from app.api.routers.auth import AuthRouter

from .ai import AiRouter
from .analytics import AnalyticsRouter
from .base import BaseRouter
from .blockchain import BlockchainRouter
from .status import StatusRouter
from .websocket import WebsocketRouter

base_router = BaseRouter().router
ai_router = AiRouter().router
blockchain_router = BlockchainRouter().router
status_router = StatusRouter().router
websocket_router = WebsocketRouter().router
auth_router = AuthRouter().router
analytics_router = AnalyticsRouter().router
