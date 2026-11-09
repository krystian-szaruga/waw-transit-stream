from __future__ import annotations

from fastapi import WebSocket


class ConnectionHub:

    def __init__(self) -> None:
        pass

    async def connect(self, websocket: WebSocket) -> None:
        pass

    async def disconnect(self, websocket: WebSocket) -> None:
        pass

    async def send(self, websocket: WebSocket, payload: object) -> None:
        pass

    async def broadcast(self, payload: object) -> None:
        pass
