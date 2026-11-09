from __future__ import annotations

from fastapi import APIRouter, Depends

from waw_transit_backend.adapters.inbound.http.dependencies import (
    get_line_service,
    get_vehicle_service,
)
from waw_transit_backend.adapters.inbound.http.schemas import LineResponse, VehicleResponse
from waw_transit_backend.application.services import LineService, VehicleService
from waw_transit_backend.domain import LineView, VehicleView

router = APIRouter(tags=["lines"])


@router.get("/lines", response_model=list[LineResponse])
def list_lines(service: LineService = Depends(get_line_service)) -> list[LineResponse]:
    return [_to_response(line) for line in service.all()]


@router.get("/lines/{vehicle_type}/{line}/vehicles", response_model=list[VehicleResponse])
def list_line_vehicles(
    vehicle_type: int,
    line: str,
    service: VehicleService = Depends(get_vehicle_service),
) -> list[VehicleResponse]:
    return [
        _to_vehicle_response(vehicle)
        for vehicle in service.by_line(vehicle_type, line)
    ]


def _to_response(line: LineView) -> LineResponse:
    return LineResponse(name=line.name, vehicle_type=line.vehicle_type)


def _to_vehicle_response(vehicle: VehicleView) -> VehicleResponse:
    return VehicleResponse(
        id=vehicle.id,
        type=vehicle.type,
        number=vehicle.number,
        line=vehicle.line,
        brigade=vehicle.brigade,
        trip_id=vehicle.trip_id,
        delay_sec=vehicle.delay_sec,
        status=vehicle.status,
        next_stop=vehicle.next_stop,
        lat=vehicle.lat,
        lon=vehicle.lon,
    )
