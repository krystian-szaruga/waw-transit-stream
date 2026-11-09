from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from waw_transit.core import ReadRepository, StopDepartureRecord
from waw_transit.core.models.static_state import StopInfo, TripStop
from waw_transit_backend.application.ports import Clock
from waw_transit_backend.domain import DepartureView, NotFoundError


class DepartureService:

    def __init__(
        self,
        departures: ReadRepository[str, Sequence[StopDepartureRecord]],
        stop_by_id: ReadRepository[str, StopInfo | None],
        trip_stops: ReadRepository[str, Sequence[TripStop]],
        clock: Clock,
    ) -> None:
        self._departures = departures
        self._stop_by_id = stop_by_id
        self._trip_stops = trip_stops
        self._clock = clock

    def for_stop(self, stop_id: str, limit: int = 20) -> Sequence[DepartureView]:
        if self._stop_by_id.load(stop_id) is None:
            raise NotFoundError(f"Stop {stop_id} not found")
        now = self._clock.now()
        records: Sequence[StopDepartureRecord] = self._departures.load(stop_id)
        termini: dict[str, str] = {}
        views: list[DepartureView] = []
        for record in records[:limit]:
            direction = termini.setdefault(record.trip_id, self._terminus(record.trip_id))
            views.append(_to_view(record, direction, now))
        return tuple(views)

    def _terminus(self, trip_id: str) -> str:
        stops: Sequence[TripStop] = self._trip_stops.load(trip_id)
        if not stops:
            return ""
        return max(stops, key=lambda stop: stop.sequence).name


def _to_view(record: StopDepartureRecord, direction: str, now: datetime) -> DepartureView:
    predicted = record.predicted.astimezone(record.scheduled.tzinfo)
    return DepartureView(
        stop_id=record.stop_id,
        line=record.line,
        direction=direction,
        vehicle_id=record.vehicle_id,
        scheduled=record.scheduled,
        predicted=predicted,
        minutes=int((predicted - now).total_seconds() // 60),
        delay_sec=(predicted - record.scheduled).total_seconds(),
    )
