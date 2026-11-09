from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from waw_transit.core import ReadRepository
from waw_transit_backend.domain import NotFoundError, TripStopsQuery, TripStopView


class TripService:

    def __init__(self, trip_stops: ReadRepository[TripStopsQuery, Sequence[TripStopView]]) -> None:
        self._trip_stops = trip_stops

    def stops(self, trip_id: str, service_date: date) -> Sequence[TripStopView]:
        stops = self._trip_stops.load(TripStopsQuery(trip_id, service_date))
        if not stops:
            raise NotFoundError(f"Trip {trip_id} not found")
        return tuple(sorted(stops, key=lambda item: item.sequence))
