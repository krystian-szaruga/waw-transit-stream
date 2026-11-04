from dataclasses import replace
from datetime import date, timedelta

import pandas as pd

from gtfs.loader import TimetableLoader


class _RecordingRepository:
    def __init__(self) -> None:
        self.saved: pd.DataFrame | None = None

    def save(self, data: pd.DataFrame) -> int:
        self.saved = data
        return len(data)


def test_when_loader_runs_then_repository_saves_today_and_tomorrow(gtfs_feed):
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
    feed = replace(gtfs_feed, calendar_dates=calendar)
    repository = _RecordingRepository()

    loaded = TimetableLoader(repository).run(feed)

    assert loaded == len(repository.saved)
    assert loaded == 10
    assert set(repository.saved["service_date"]) == {today, tomorrow}
