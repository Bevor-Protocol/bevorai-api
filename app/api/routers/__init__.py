from .ai import AiRouter
from .blockchain import BlockchainRouter
from .health import HealthRouter
from .status import StatusRouter
from .websocket import WebsocketRouter

health_router = HealthRouter().router
ai_router = AiRouter().router
blockchain_router = BlockchainRouter().router
status_router = StatusRouter().router
websocket_router = WebsocketRouter().router
