from __future__ import annotations

from fastapi import APIRouter, WebSocket

from waw_transit_backend.adapters.inbound.websocket.hub import ConnectionHub

router = APIRouter()
hub = ConnectionHub()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    pass
