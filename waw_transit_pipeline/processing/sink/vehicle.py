from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pyspark.sql import Row

from waw_transit_pipeline.processing.assignment.records import TripId, VehicleKey
from waw_transit_pipeline.processing.model import TripMatchCol


@dataclass(frozen=True, slots=True)
class VehicleUpdate:
    vehicle_type: int
    vehicle_number: str
    line: str
    brigade: str
    trip_id: TripId
    delay: float
    next_sequence: int
    gtfs_version: int
    timestamp: datetime
    lat: float
    lon: float
    match_status: str

    @property
    def key(self) -> VehicleKey:
        return VehicleKey(self.vehicle_type, self.vehicle_number)

    def is_newer_than(self, other: VehicleUpdate) -> bool:
        return self.timestamp > other.timestamp

    @classmethod
    def from_row(cls, row: Row) -> VehicleUpdate:
        return cls(
            vehicle_type=int(cls._required(row, TripMatchCol.VEHICLE_TYPE)),
            vehicle_number=str(cls._required(row, TripMatchCol.VEHICLE_NUMBER)),
            line=str(cls._required(row, TripMatchCol.LINE)),
            brigade=str(row[TripMatchCol.BRIGADE.value]),
            trip_id=TripId(str(cls._required(row, TripMatchCol.TRIP_ID))),
            delay=float(row[TripMatchCol.DELAY_SEC.value]),
            next_sequence=int(row[TripMatchCol.NEXT_STOP_SEQUENCE.value]),
            gtfs_version=int(row[TripMatchCol.GTFS_VERSION.value]),
            timestamp=row[TripMatchCol.API_TS.value],
            lat=float(row[TripMatchCol.LAT.value]),
            lon=float(row[TripMatchCol.LON.value]),
            match_status=str(row[TripMatchCol.MATCH_STATUS.value]),
        )

    @staticmethod
    def _required(row: Row, column: TripMatchCol) -> str | int:
        value = row[column.value]
        if value is None:
            raise ValueError(f"Missing {column.value}")
        return value


class VehicleValidation:
    _LAT_RANGE = (51.8, 52.6)
    _LON_RANGE = (20.5, 21.5)
    _FUTURE_GRACE_SEC = 60
    _STALE_SEC = 180

    def __init__(self, timezone: str) -> None:
        self._tz = ZoneInfo(timezone)

    def validate(self, row: Row) -> VehicleUpdate | None:
        try:
            update = VehicleUpdate.from_row(row)
        except (TypeError, ValueError):
            return None
        return update if self._is_valid(update) else None

    def _is_valid(self, update: VehicleUpdate) -> bool:
        return (
            bool(update.vehicle_number)
            and bool(update.line)
            and bool(update.trip_id)
            and math.isfinite(update.delay)
            and math.isfinite(update.lat)
            and math.isfinite(update.lon)
            and self._LAT_RANGE[0] <= update.lat <= self._LAT_RANGE[1]
            and self._LON_RANGE[0] <= update.lon <= self._LON_RANGE[1]
            and update.next_sequence > 0
            and self._is_fresh(update.timestamp)
        )

    def _is_fresh(self, timestamp: object) -> bool:
        if not isinstance(timestamp, datetime):
            return False
        moment = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=self._tz)
        now = datetime.now(self._tz)
        return (
            now - timedelta(seconds=self._STALE_SEC)
            <= moment
            <= now + timedelta(seconds=self._FUTURE_GRACE_SEC)
        )