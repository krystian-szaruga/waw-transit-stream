from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from waw_transit.core import ReadRepository
from waw_transit_backend.domain import NotFoundError, ShapePoint, TripStopsQuery, TripStopView


class TripService:

    def __init__(
        self,
        trip_stops: ReadRepository[TripStopsQuery, Sequence[TripStopView]],
        trip_shape: ReadRepository[str, Sequence[ShapePoint]],
    ) -> None:
        self._trip_stops = trip_stops
        self._trip_shape = trip_shape

    def stops(self, trip_id: str, service_date: date) -> Sequence[TripStopView]:
        stops = self._trip_stops.load(TripStopsQuery(trip_id, service_date))
        if not stops:
            raise NotFoundError(f"Trip {trip_id} not found")
        return tuple(sorted(stops, key=lambda item: item.sequence))

    def shape(self, trip_id: str) -> Sequence[ShapePoint]:
        return tuple(sorted(self._trip_shape.load(trip_id), key=lambda item: item.sequence))
