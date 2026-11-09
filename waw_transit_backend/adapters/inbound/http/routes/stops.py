from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from waw_transit_backend.adapters.inbound.http.dependencies import (
    get_departure_service,
    get_stop_service,
)
from waw_transit_backend.adapters.inbound.http.schemas import DepartureResponse, StopResponse
from waw_transit_backend.application.services import DepartureService, StopService

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("", response_model=list[StopResponse])
def list_stops(
    query: str | None = None,
    service: StopService = Depends(get_stop_service),
) -> list[StopResponse]:
    pass


@router.get("/{stop_id}", response_model=StopResponse)
def get_stop(
    stop_id: str,
    service: StopService = Depends(get_stop_service),
) -> StopResponse:
    pass


@router.get("/{stop_id}/departures", response_model=list[DepartureResponse])
def list_departures(
    stop_id: str,
    limit: int = Query(20, ge=1),
    service: DepartureService = Depends(get_departure_service),
) -> list[DepartureResponse]:
    pass
