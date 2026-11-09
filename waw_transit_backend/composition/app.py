from __future__ import annotations

from fastapi import FastAPI

from waw_transit_backend.adapters.inbound.http.errors import register_error_handlers
from waw_transit_backend.adapters.inbound.http.routes import stops
from waw_transit_backend.composition.container import create_container


def create_app() -> FastAPI:
    app = FastAPI()
    app.state.container = create_container()
    register_error_handlers(app)
    app.include_router(stops.router)
    return app
