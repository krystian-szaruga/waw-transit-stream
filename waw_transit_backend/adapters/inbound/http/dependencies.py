from __future__ import annotations

from fastapi import Request

from waw_transit_backend.application.services import (
    DepartureService,
    LineService,
    StopService,
    VehicleService,
)


def get_vehicle_service(request: Request) -> VehicleService:
    pass


def get_stop_service(request: Request) -> StopService:
    return request.app.state.container.stop_service


def get_departure_service(request: Request) -> DepartureService:
    pass


def get_line_service(request: Request) -> LineService:
    pass
