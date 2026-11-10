from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from waw_transit_backend.adapters.inbound.http.dependencies import (
    get_departure_service,
    get_stop_service,
)
from waw_transit_backend.adapters.inbound.http.schemas import DepartureResponse, StopResponse
from waw_transit_backend.application.services import DepartureService, StopService
from waw_transit_backend.domain import DepartureView, StopView

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("", response_model=list[StopResponse])
def list_stops(
    query: str | None = None,
    service: StopService = Depends(get_stop_service),
) -> list[StopResponse]:
    return [_to_response(stop) for stop in service.search(query)]


@router.get("/{stop_id}", response_model=StopResponse)
def get_stop(
    stop_id: str,
    service: StopService = Depends(get_stop_service),
) -> StopResponse:
    return _to_response(service.get(stop_id))


@router.get("/{stop_id}/departures", response_model=list[DepartureResponse])
def list_departures(
    stop_id: str,
    limit: int = Query(20, ge=1),
    service: DepartureService = Depends(get_departure_service),
) -> list[DepartureResponse]:
    return [
        _to_departure_response(departure)
        for departure in service.for_stop(stop_id, limit)
    ]


def _to_response(stop: StopView) -> StopResponse:
    return StopResponse(
        id=stop.id,
        name=stop.name,
        lat=stop.lat,
        lon=stop.lon,
    )


def _to_departure_response(departure: DepartureView) -> DepartureResponse:
    return DepartureResponse(
        stop_id=departure.stop_id,
        line=departure.line,
        direction=departure.direction,
        trip_id=departure.trip_id,
        stop_sequence=departure.stop_sequence,
        vehicle_next_sequence=departure.vehicle_next_sequence,
        vehicle_id=departure.vehicle_id,
        scheduled=departure.scheduled,
        predicted=departure.predicted,
        scheduled_minutes=departure.scheduled_minutes,
        minutes=departure.minutes,
        delay_sec=departure.delay_sec,
        live=departure.live,
    )
