from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

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

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    hub: ConnectionHub = websocket.app.state.hub
    container = websocket.app.state.container
    service: LiveFeedService = container.live_feed_service
    queue = await hub.connect(websocket)
    try:
        message = SubscribeMessage.model_validate(await websocket.receive_json())
        snapshot = await asyncio.to_thread(service.snapshot, message.stop_id, message.line)
        version = await asyncio.to_thread(container.active_version.load)
        sent_version = _log_version(None, version)
        await hub.send(websocket, _snapshot_message(snapshot, version))
        while True:
            items = await _next_update(websocket, queue)
            filtered = await asyncio.to_thread(_for_subscription, items, message, service)
            version = await asyncio.to_thread(container.active_version.load)
            sent_version = _log_version(sent_version, version)
            await hub.send(websocket, _update_message(filtered, version))
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(websocket)


async def _next_update(
    websocket: WebSocket,
    queue: asyncio.Queue[list[VehicleView | DepartureView]],
) -> list[VehicleView | DepartureView]:
    while True:
        update = asyncio.create_task(queue.get())
        receive = asyncio.create_task(websocket.receive())
        done, _ = await asyncio.wait({update, receive}, return_when=asyncio.FIRST_COMPLETED)
        if update in done:
            receive.cancel()
            with suppress(asyncio.CancelledError):
                await receive
            return update.result()
        update.cancel()
        with suppress(asyncio.CancelledError):
            await update
        message = receive.result()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", 1000))


def _log_version(sent: int | None, current: int | None) -> int | None:
    if current is not None and current != sent:
        logger.info("Sending timetable version %d to the client", current)
        return current
    return sent


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


def _snapshot_message(
    items: list[VehicleView | DepartureView], version: int | None
) -> SnapshotMessage:
    vehicles, departures = _split(items)
    return SnapshotMessage(vehicles=vehicles, departures=departures, version=version)


def _update_message(
    items: list[VehicleView | DepartureView], version: int | None
) -> UpdateMessage:
    vehicles, departures = _split(items)
    return UpdateMessage(vehicles=vehicles, departures=departures, version=version)


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
