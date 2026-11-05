from datetime import date

import pandas as pd
import pytest

from core import ReadRepository
from processing.lookup import LookupLoader


class _FrameRepository(ReadRepository):
    def __init__(self, frame: pd.DataFrame, version_id: int = 7) -> None:
        super().__init__(None)
        self._frame = frame
        self._version_id = version_id

    def load(self, payload=None) -> tuple[pd.DataFrame, int]:
        return self._frame, self._version_id


@pytest.fixture
def load_lookup():
    def _load(frame: pd.DataFrame, version_id: int = 7):
        return LookupLoader(_FrameRepository(frame, version_id)).load()

    return _load


@pytest.fixture
def timetable_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "service_date": [date(2026, 11, 4)] * 4,
            "vehicle_type": [1, 1, 2, 2],
            "line": ["175", "175", "9", "9"],
            "brigade": ["1", "1", "3", "3"],
            "route_id": ["r1", "r1", "r2", "r2"],
            "trip_id": ["t1", "t1", "t2", "t2"],
            "stop_id": ["1001", "1002", "2001", "2002"],
            "stop_name": ["Start", "End", "Most", "Rondo"],
            "stop_sequence": [1, 2, 1, 2],
            "stop_lat": [52.23, 52.23, 52.25, 52.25],
            "stop_lon": [21.0, 21.006, 21.02, 21.03],
            "scheduled_arrival_offset": [86400, 88000, 28800, 29400],
        }
    )
