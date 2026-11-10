from dataclasses import replace
from datetime import date, timedelta

import pandas as pd

from waw_transit.core import GtfsPayload
from waw_transit_pipeline.gtfs.loader import TimetableLoader

_SHA = "a" * 64


class _RecordingRepository:
    def __init__(self) -> None:
        self.timetable: pd.DataFrame | None = None
        self.trip_shapes: pd.DataFrame | None = None
        self.shape_points: pd.DataFrame | None = None
        self.sha256: str | None = None

    def save(self, data: GtfsPayload[pd.DataFrame]) -> int:
        self.timetable = data.timetable
        self.trip_shapes = data.trip_shapes
        self.shape_points = data.shape_points
        self.sha256 = data.sha256
        return len(data.timetable)


def _feed_for_today(gtfs_feed):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    calendar = pd.DataFrame(
        {
            "service_id": ["S-WEEKDAY", "S-WEEKDAY", "S-TOMORROW"],
            "date": [
                today.strftime("%Y%m%d"),
                tomorrow.strftime("%Y%m%d"),
                tomorrow.strftime("%Y%m%d"),
            ],
            "exception_type": ["1", "1", "1"],
        }
    )
    return replace(gtfs_feed, calendar_dates=calendar)


def test_when_loader_runs_then_repository_saves_today_and_tomorrow(gtfs_feed):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    repository = _RecordingRepository()

    loaded = TimetableLoader(repository).run(_feed_for_today(gtfs_feed), _SHA)

    assert loaded == len(repository.timetable)
    assert loaded == 10
    assert repository.sha256 == _SHA
    assert set(repository.timetable["service_date"]) == {today, tomorrow}


def test_when_loader_runs_then_shapes_of_saved_trips_are_saved_as_well(gtfs_feed):
    repository = _RecordingRepository()

    TimetableLoader(repository).run(_feed_for_today(gtfs_feed), _SHA)

    assert set(repository.trip_shapes["trip_id"]) == set(repository.timetable["trip_id"])
    assert set(repository.shape_points["shape_id"]) == set(repository.trip_shapes["shape_id"])
