from __future__ import annotations

from fastapi import APIRouter, Depends

from waw_transit_backend.adapters.inbound.http.dependencies import get_vehicle_service
from waw_transit_backend.adapters.inbound.http.schemas import VehicleResponse
from waw_transit_backend.application.services import VehicleService

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleResponse])
def list_vehicles(service: VehicleService = Depends(get_vehicle_service)) -> list[VehicleResponse]:
    pass


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: str,
    service: VehicleService = Depends(get_vehicle_service),
) -> VehicleResponse:
    pass
