import asyncio
import hashlib
import hmac
import json
import logging
import os
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from redis.client import PubSub

from app.cache import redis_client

secret = os.getenv("SHARED_SECRET")


class WebsocketRouter:
    HEARTBEAT_INTERVAL = 5

    def __init__(self):
        self.router = APIRouter(include_in_schema=False)
        self.active_connections: list[WebSocket] = []
        self.pending_jobs = {}
        self.inverse_jobs = defaultdict(list)
        self.heartbeat_check = {}
        self.register_routes()

    def register_routes(self):
        self.router.add_websocket_route("/ws", self.websocket)

    async def websocket(self, websocket: WebSocket):
        try:
            await self.require_auth(websocket)
            pubsub = redis_client.pubsub()
            pubsub.subscribe("evals")
            while True:
                raw_message = await websocket.receive_text()
                message = str(raw_message).strip()
                if message.startswith("subscribe:"):
                    job_id = message.split(":")[1]
                    logging.info(f"WS subscribed to job {job_id}")
                    self.assign_job(job_id, websocket)
                elif message == "PONG":
                    self.heartbeat_check[websocket] = False
                message = pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )

                if message:
                    data = json.loads(message["data"])
                    identifier = data["id"]
                    if self.is_job_owner(identifier, websocket):
                        await self.send_personal_message(
                            {"type": "data", "result": data["result"]}, websocket
                        )

        except WebSocketDisconnect:
            await self.disconnect(websocket, pubsub)
        except WebSocketException as e:
            logging.error(f"WebSocket error: {e}")
            await websocket.close(code=4001)

    async def require_auth(self, websocket: WebSocket):
        signature = websocket.query_params.get("signature")
        timestamp = websocket.query_params.get("timestamp")

        current_time = int(datetime.now().timestamp() * 1000)
        timestamp_int = int(timestamp)
        if abs(current_time - timestamp_int) <= 300:  # Allow a 5-minute window
            payload = f"{timestamp}:{websocket.url.path}"
            expected_signature = hmac.new(
                secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(signature, expected_signature):
                await self.connect(websocket)
                return
        raise WebSocketException("invalid auth")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(
            "New WS connection, current connection count:"
            f" {len(self.active_connections)}"
        )
        self.heartbeat_check[websocket] = False
        asyncio.create_task(self.heartbeat(websocket))

    def assign_job(self, job_id: str, websocket: WebSocket):
        self.pending_jobs[job_id] = websocket
        self.inverse_jobs[websocket].append(job_id)

    def is_job_owner(self, job_id: str, websocket: WebSocket):
        return job_id in self.inverse_jobs[websocket]

    async def disconnect(self, websocket: WebSocket, pubsub: PubSub):
        self.active_connections.remove(websocket)
        for job_id in self.inverse_jobs[websocket]:
            del self.pending_jobs[job_id]
        del self.inverse_jobs[websocket]
        del self.heartbeat_check[websocket]
        pubsub.unsubscribe("evals")

    async def send_personal_message(self, data: str, websocket: WebSocket):
        await websocket.send_json(data)

    async def heartbeat(self, websocket: WebSocket):
        while True:
            # Time in between pings
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            try:
                if websocket.client_state.name == "DISCONNECTED":
                    return
                await self.send_personal_message({"type": "heartbeat"}, websocket)
                self.heartbeat_check[websocket] = True

                # time allotted for the client to respond properly.
                await asyncio.sleep(3)
                if (
                    websocket in self.heartbeat_check
                    and self.heartbeat_check[websocket]
                ):
                    print("Client unresponsive, closing connection")
                    raise WebSocketException(code=1001)
            except WebSocketException:
                # Don't know what this id is actually based off of.
                await websocket.close()
                break
