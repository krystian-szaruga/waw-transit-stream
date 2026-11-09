from __future__ import annotations

from fastapi import APIRouter, Depends

from waw_transit_backend.adapters.inbound.http.dependencies import get_vehicle_service
from waw_transit_backend.adapters.inbound.http.schemas import VehicleResponse
from waw_transit_backend.application.services import VehicleService
from waw_transit_backend.domain import VehicleView

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleResponse])
def list_vehicles(service: VehicleService = Depends(get_vehicle_service)) -> list[VehicleResponse]:
    return [_to_response(vehicle) for vehicle in service.all()]


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: str,
    service: VehicleService = Depends(get_vehicle_service),
) -> VehicleResponse:
    return _to_response(service.get(vehicle_id))


def _to_response(vehicle: VehicleView) -> VehicleResponse:
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
