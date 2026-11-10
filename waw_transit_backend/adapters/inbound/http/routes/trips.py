from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from waw_transit_backend.adapters.inbound.http.dependencies import get_trip_service
from waw_transit_backend.adapters.inbound.http.schemas import TripStopResponse
from waw_transit_backend.application.services import TripService
from waw_transit_backend.domain import TripStopView

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/{trip_id}/stops", response_model=list[TripStopResponse])
def list_trip_stops(
    trip_id: str,
    service: TripService = Depends(get_trip_service),
    service_date: date = Query(alias="date"),
) -> list[TripStopResponse]:
    return [_to_response(stop) for stop in service.stops(trip_id, service_date)]


def _to_response(stop: TripStopView) -> TripStopResponse:
    return TripStopResponse(sequence=stop.sequence, name=stop.name, scheduled=stop.scheduled)
