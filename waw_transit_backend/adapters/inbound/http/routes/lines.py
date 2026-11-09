from __future__ import annotations

from fastapi import APIRouter, Depends

from waw_transit_backend.adapters.inbound.http.dependencies import (
    get_line_service,
    get_vehicle_service,
)
from waw_transit_backend.adapters.inbound.http.schemas import LineResponse, VehicleResponse
from waw_transit_backend.application.services import LineService, VehicleService

router = APIRouter(tags=["lines"])


@router.get("/lines", response_model=list[LineResponse])
def list_lines(service: LineService = Depends(get_line_service)) -> list[LineResponse]:
    pass


@router.get("/lines/{vehicle_type}/{line}/vehicles", response_model=list[VehicleResponse])
def list_line_vehicles(
    vehicle_type: int,
    line: str,
    service: VehicleService = Depends(get_vehicle_service),
) -> list[VehicleResponse]:
    pass
