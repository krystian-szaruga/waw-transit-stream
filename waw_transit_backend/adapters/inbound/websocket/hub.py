from __future__ import annotations

import asyncio

from fastapi import WebSocket
from pydantic import BaseModel

from waw_transit_backend.domain import DepartureView, VehicleView


class ConnectionHub:

    def __init__(self) -> None:
        self._queues: dict[WebSocket, asyncio.Queue[list[VehicleView | DepartureView]]] = {}

    async def connect(self, websocket: WebSocket) -> asyncio.Queue[list[VehicleView | DepartureView]]:
        await websocket.accept()
        queue: asyncio.Queue[list[VehicleView | DepartureView]] = asyncio.Queue()
        self._queues[websocket] = queue
        return queue

    async def disconnect(self, websocket: WebSocket) -> None:
        self._queues.pop(websocket, None)

    @staticmethod
    async def send(websocket: WebSocket, payload: BaseModel) -> None:
        await websocket.send_json(payload.model_dump(mode="json"))

    async def broadcast(self, items: list[VehicleView | DepartureView]) -> None:
        for queue in tuple(self._queues.values()):
            queue.put_nowait(items)
