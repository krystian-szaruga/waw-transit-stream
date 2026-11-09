from __future__ import annotations

import logging
from collections.abc import ValuesView
from zoneinfo import ZoneInfo

import pyspark.sql.functions as F
from pyspark.sql import DataFrame

from waw_transit.core.models import LiveStateBatch, StopDeparture, VehicleSnapshot
from waw_transit_pipeline.processing.assignment.records import TripId
from waw_transit_pipeline.processing.model import Lookup, MatchStatus, TripMatchCol

from .schedule import TripSchedule
from .vehicle import VehicleValidation

logger = logging.getLogger("warsaw_transit_stream_processing")


class LiveStatePreparer:
    def __init__(self, lookup: Lookup, timezone: str) -> None:
        self._tz = ZoneInfo(timezone)
        self._validation = VehicleValidation(timezone)
        self._schedules: dict[TripId, TripSchedule] = {
            TripId(trip.trip_id): TripSchedule(trip, self._tz) for trip in lookup
        }

    def prepare(self, frame: DataFrame) -> LiveStateBatch:
        vehicles = tuple(_Batch(frame, self._validation).latest_vehicles())
        departures: dict[str, tuple[StopDeparture, ...]] = {}
        for vehicle in vehicles:
            schedule = self._schedules.get(TripId(vehicle.trip_id))
            if schedule is not None:
                departures[vehicle.vehicle_id] = tuple(
                    schedule.departures(vehicle.delay, vehicle.next_sequence)
                )
        return LiveStateBatch(
            vehicles=vehicles,
            departures=departures,
        )


class _Batch:
    def __init__(self, frame: DataFrame, validation: VehicleValidation) -> None:
        self._frame = frame
        self._validation = validation

    def latest_vehicles(self) -> ValuesView[VehicleSnapshot]:
        status = TripMatchCol.MATCH_STATUS.value
        latest: dict[str, VehicleSnapshot] = {}
        rejected = 0
        for row in self._frame.where(F.col(status) == MatchStatus.MATCHED.value).collect():
            snapshot = self._validation.validate(row)
            if snapshot is None:
                rejected += 1
                continue
            held = latest.get(snapshot.vehicle_id)
            if held is None or snapshot.timestamp > held.timestamp:
                latest[snapshot.vehicle_id] = snapshot
        if rejected:
            logger.warning("Rejected %d invalid vehicle rows in batch", rejected)
        return latest.values()
