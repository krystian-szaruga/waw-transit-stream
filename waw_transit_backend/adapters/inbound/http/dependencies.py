from __future__ import annotations

from fastapi import Request

from waw_transit_backend.application.services import (
    DepartureService,
    LineService,
    StopService,
    TripService,
    VehicleService,
)


def get_vehicle_service(request: Request) -> VehicleService:
    return request.app.state.container.vehicle_service


def get_stop_service(request: Request) -> StopService:
    return request.app.state.container.stop_service


def get_departure_service(request: Request) -> DepartureService:
    return request.app.state.container.departure_service


def get_line_service(request: Request) -> LineService:
    return request.app.state.container.line_service


def get_trip_service(request: Request) -> TripService:
    return request.app.state.container.trip_service
