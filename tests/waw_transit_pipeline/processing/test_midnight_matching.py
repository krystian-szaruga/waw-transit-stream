from datetime import date

import pandas as pd

from waw_transit.core import ReadRepository
from waw_transit_pipeline.processing.assignment.records import MatchState
from waw_transit_pipeline.processing.assignment.trip_matcher import TripMatcher
from waw_transit_pipeline.processing.lookup import LookupLoader

_SERVICE_DATE = date(2026, 11, 4)
_LON_START, _LON_END = 21.0, 21.006
_LAT = 52.23
_TRIP = "t-after-midnight"


class _StopsRepository(ReadRepository):
    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def load(self, payload=None) -> tuple[pd.DataFrame, int]:
        return self._frame, 7


def _timetable() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "service_date": [_SERVICE_DATE, _SERVICE_DATE],
            "vehicle_type": [1, 1],
            "line": ["175", "175"],
            "brigade": ["1", "1"],
            "route_id": ["r1", "r1"],
            "trip_id": [_TRIP, _TRIP],
            "stop_id": ["1001", "1002"],
            "stop_name": ["Start", "End"],
            "stop_sequence": [1, 2],
            "stop_lat": [_LAT, _LAT],
            "stop_lon": [_LON_START, _LON_END],
            "scheduled_arrival_offset": [86400, 88000],
        }
    )


def _ping(timestamp: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "vehicle_type": [1],
            "VehicleNumber": ["1001"],
            "Brigade": ["1"],
            "Lines": ["175"],
            "Lon": [21.003],
            "Lat": [_LAT],
            "Time": [pd.Timestamp(timestamp)],
        }
    )


def test_when_ping_arrives_after_midnight_then_it_matches_the_previous_service_day_trip():
    snapshot = LookupLoader(_StopsRepository(_timetable())).load()

    row, _, _ = TripMatcher(snapshot.lookup, snapshot.version_id).match_rows(_ping("2026-11-05 00:20:00"), MatchState())

    assert snapshot.version_id == 7
    assert row[10] == 7
    assert row[4] == _TRIP
    assert abs(row[6] - 400.0) <= 1.0
