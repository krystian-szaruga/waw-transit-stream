from __future__ import annotations

import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pyspark.sql import Row

from waw_transit.core.models import VehicleSnapshot
from waw_transit_pipeline.processing.model import TripMatchCol


class VehicleValidation:
    _LAT_RANGE = (51.8, 52.6)
    _LON_RANGE = (20.5, 21.5)
    _FUTURE_GRACE_SEC = 60
    _STALE_SEC = 180

    def __init__(self, timezone: str) -> None:
        self._tz = ZoneInfo(timezone)

    def validate(self, row: Row) -> VehicleSnapshot | None:
        try:
            snapshot = self._from_row(row)
        except (TypeError, ValueError):
            return None
        return snapshot if self._is_valid(snapshot) else None

    @staticmethod
    def _from_row(row: Row) -> VehicleSnapshot:
        return VehicleSnapshot(
            vehicle_type=int(_required(row, TripMatchCol.VEHICLE_TYPE)),
            vehicle_number=str(_required(row, TripMatchCol.VEHICLE_NUMBER)),
            line=str(_required(row, TripMatchCol.LINE)),
            brigade=str(row[TripMatchCol.BRIGADE.value]),
            trip_id=str(_required(row, TripMatchCol.TRIP_ID)),
            delay=float(row[TripMatchCol.DELAY_SEC.value]),
            next_sequence=int(row[TripMatchCol.NEXT_STOP_SEQUENCE.value]),
            gtfs_version=int(row[TripMatchCol.GTFS_VERSION.value]),
            timestamp=row[TripMatchCol.API_TS.value],
            lat=float(row[TripMatchCol.LAT.value]),
            lon=float(row[TripMatchCol.LON.value]),
            match_status=str(row[TripMatchCol.MATCH_STATUS.value]),
        )

    def _is_valid(self, snapshot: VehicleSnapshot) -> bool:
        return (
            bool(snapshot.vehicle_number)
            and bool(snapshot.line)
            and bool(snapshot.trip_id)
            and math.isfinite(snapshot.delay)
            and math.isfinite(snapshot.lat)
            and math.isfinite(snapshot.lon)
            and self._LAT_RANGE[0] <= snapshot.lat <= self._LAT_RANGE[1]
            and self._LON_RANGE[0] <= snapshot.lon <= self._LON_RANGE[1]
            and snapshot.next_sequence > 0
            and self._is_fresh(snapshot.timestamp)
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


def _required(row: Row, column: TripMatchCol) -> str | int:
    value = row[column.value]
    if value is None:
        raise ValueError(f"Missing {column.value}")
    return value
