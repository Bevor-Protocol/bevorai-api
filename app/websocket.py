import asyncio
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from redis.client import PubSub

from .cache import redis_client

router = APIRouter()

HEARTBEAT_INTERVAL = 5


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.pending_jobs = {}
        self.inverse_jobs = defaultdict(list)
        self.heartbeat_check = {}

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
            await asyncio.sleep(HEARTBEAT_INTERVAL)
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


manager = ConnectionManager()

"""
Only intended to be used via the certaik App.
All 3rd party developers will rely on Polling OR Webhooks
"""


@router.websocket("/ws")
async def websocket(websocket: WebSocket):
    await manager.connect(websocket)
    pubsub = redis_client.pubsub()
    pubsub.subscribe("evals")

    try:
        while True:
            raw_message = await websocket.receive_text()
            message = str(raw_message).strip()
            if message.startswith("subscribe:"):
                job_id = message.split(":")[1]
                logging.info(f"WS subscribed to job {job_id}")
                manager.assign_job(job_id, websocket)
            elif message == "PONG":
                manager.heartbeat_check[websocket] = False
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message:
                data = json.loads(message["data"])
                identifier = data["job_id"]
                if manager.is_job_owner(identifier, websocket):
                    await manager.send_personal_message(
                        {"type": "data", "result": data["result"]}, websocket
                    )

    except WebSocketDisconnect:
        await manager.disconnect(websocket, pubsub)
