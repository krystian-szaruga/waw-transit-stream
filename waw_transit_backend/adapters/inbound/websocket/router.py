from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketDisconnect

from waw_transit_backend.adapters.inbound.http.schemas import DepartureResponse, VehicleResponse
from waw_transit_backend.adapters.inbound.websocket.hub import ConnectionHub
from waw_transit_backend.adapters.inbound.websocket.schemas import (
    SnapshotMessage,
    SubscribeMessage,
    UpdateMessage,
)
from waw_transit_backend.application.services import LiveFeedService
from waw_transit_backend.domain import DepartureView, VehicleView

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    hub: ConnectionHub = websocket.app.state.hub
    service: LiveFeedService = websocket.app.state.container.live_feed_service
    queue = await hub.connect(websocket)
    try:
        message = SubscribeMessage.model_validate(await websocket.receive_json())
        snapshot = await asyncio.to_thread(service.snapshot, message.stop_id, message.line)
        await hub.send(websocket, _snapshot_message(snapshot))
        while True:
            items = await queue.get()
            filtered = await asyncio.to_thread(_for_subscription, items, message, service)
            await hub.send(websocket, _update_message(filtered))
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(websocket)


def _for_subscription(
    items: list[VehicleView | DepartureView],
    message: SubscribeMessage,
    service: LiveFeedService,
) -> list[VehicleView | DepartureView]:
    departures: list[VehicleView | DepartureView] = [
        item
        for item in items
        if isinstance(item, VehicleView)
        and (message.line is None or item.line == message.line)
    ]
    if message.stop_id is None:
        return departures
    return departures + list(service.departures_for(message.stop_id))


def _snapshot_message(items: list[VehicleView | DepartureView]) -> SnapshotMessage:
    vehicles, departures = _split(items)
    return SnapshotMessage(vehicles=vehicles, departures=departures)


def _update_message(items: list[VehicleView | DepartureView]) -> UpdateMessage:
    vehicles, departures = _split(items)
    return UpdateMessage(vehicles=vehicles, departures=departures)


def _split(
    items: list[VehicleView | DepartureView],
) -> tuple[list[VehicleResponse], list[DepartureResponse]]:
    vehicles: list[VehicleResponse] = [
        VehicleResponse.model_validate(item, from_attributes=True)
        for item in items
        if isinstance(item, VehicleView)
    ]
    departures: list[DepartureResponse] = [
        DepartureResponse.model_validate(item, from_attributes=True)
        for item in items
        if isinstance(item, DepartureView)
    ]
    return vehicles, departures
