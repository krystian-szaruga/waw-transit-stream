from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime, timedelta

from waw_transit.core import ReadRepository, StopDepartureRecord, VehicleSnapshot
from waw_transit.core.models.static_state import StopInfo, TripStop
from waw_transit_backend.application.ports import Clock
from waw_transit_backend.domain import (
    DepartureView,
    NotFoundError,
    ScheduleQuery,
    ScheduledDeparture,
)


class DepartureService:

    def __init__(
        self,
        departures: ReadRepository[str, Sequence[StopDepartureRecord]],
        schedule: ReadRepository[ScheduleQuery, Sequence[ScheduledDeparture]],
        stop_by_id: ReadRepository[str, StopInfo | None],
        trip_stops: ReadRepository[str, Sequence[TripStop]],
        vehicles: ReadRepository[str, VehicleSnapshot | None],
        clock: Clock,
    ) -> None:
        self._departures = departures
        self._schedule = schedule
        self._stop_by_id = stop_by_id
        self._trip_stops = trip_stops
        self._vehicles = vehicles
        self._clock = clock

    def for_stop(self, stop_id: str, limit: int = 20) -> Sequence[DepartureView]:
        if self._stop_by_id.load(stop_id) is None:
            raise NotFoundError(f"Stop {stop_id} not found")
        now = self._clock.now()
        records: Sequence[StopDepartureRecord] = self._departures.load(stop_id)
        scheduled = self._schedule.load(ScheduleQuery(stop_id, (now.date(), now.date() - timedelta(days=1))))
        directions = {item.trip_id: item.direction for item in scheduled}
        live_keys = {(record.trip_id, record.stop_sequence) for record in records}
        positions: dict[str, int | None] = {}
        views: list[DepartureView] = [
            self._live_view(record, directions, positions, now)
            for record in records
        ]
        views.extend(
            _scheduled_view(item, now)
            for item in scheduled
            if (item.trip_id, item.stop_sequence) not in live_keys and item.scheduled >= now
        )
        views.sort(key=_moment)
        return tuple(views[:limit])

    def _live_view(
        self,
        record: StopDepartureRecord,
        directions: dict[str, str],
        positions: dict[str, int | None],
        now: datetime,
    ) -> DepartureView:
        direction = directions.get(record.trip_id) or self._terminus(record.trip_id)
        predicted = record.predicted.astimezone(record.scheduled.tzinfo)
        return DepartureView(
            stop_id=record.stop_id,
            line=record.line,
            direction=direction,
            trip_id=record.trip_id,
            stop_sequence=record.stop_sequence,
            vehicle_next_sequence=self._next_sequence(record.vehicle_id, positions),
            vehicle_id=record.vehicle_id,
            scheduled=record.scheduled,
            predicted=predicted,
            scheduled_minutes=_minutes((record.scheduled - now).total_seconds()),
            minutes=_minutes((predicted - now).total_seconds()),
            delay_sec=(predicted - record.scheduled).total_seconds(),
            live=True,
        )

    def _next_sequence(self, vehicle_id: str, positions: dict[str, int | None]) -> int | None:
        if vehicle_id not in positions:
            vehicle = self._vehicles.load(vehicle_id)
            positions[vehicle_id] = None if vehicle is None else vehicle.next_sequence
        return positions[vehicle_id]

    def _terminus(self, trip_id: str) -> str:
        stops: Sequence[TripStop] = self._trip_stops.load(trip_id)
        if not stops:
            return ""
        return max(stops, key=lambda stop: stop.sequence).name



def _scheduled_view(item: ScheduledDeparture, now: datetime) -> DepartureView:
    return DepartureView(
        stop_id=item.stop_id,
        line=item.line,
        direction=item.direction,
        trip_id=item.trip_id,
        stop_sequence=item.stop_sequence,
        vehicle_next_sequence=None,
        vehicle_id=None,
        scheduled=item.scheduled,
        predicted=None,
        scheduled_minutes=_minutes((item.scheduled - now).total_seconds()),
        minutes=_minutes((item.scheduled - now).total_seconds()),
        delay_sec=None,
        live=False,
    )

def _moment(view: DepartureView) -> datetime:
    return view.predicted if view.predicted is not None else view.scheduled


def _minutes(seconds: float) -> int:
    if seconds < -30:
        return -1
    if seconds <= 30:
        return 0
    return math.ceil(seconds / 60)
