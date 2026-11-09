from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from waw_transit_backend.adapters.inbound.http.errors import register_error_handlers
from waw_transit_backend.adapters.inbound.http.routes import health, lines, stops, trips, vehicles
from waw_transit_backend.adapters.inbound.websocket import router as websocket
from waw_transit_backend.adapters.inbound.websocket.hub import ConnectionHub
from waw_transit_backend.composition.container import create_container


def create_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.state.container = create_container()
    app.state.hub = ConnectionHub()
    register_error_handlers(app)
    app.include_router(stops.router)
    app.include_router(lines.router)
    app.include_router(vehicles.router)
    app.include_router(trips.router)
    app.include_router(health.router)
    app.include_router(websocket.router)
    return app


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_broadcast_updates(app))
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def _broadcast_updates(app: FastAPI) -> None:
    service = app.state.container.live_feed_service
    async for items in service.updates():
        await app.state.hub.broadcast(items)
