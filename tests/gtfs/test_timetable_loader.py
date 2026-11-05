from dataclasses import replace
from datetime import date, timedelta

import pandas as pd

from core import Payload
from gtfs.loader import TimetableLoader

_SHA = "a" * 64


class _RecordingRepository:
    def __init__(self) -> None:
        self.saved: pd.DataFrame | None = None
        self.sha256: str | None = None

    def save(self, data: Payload[pd.DataFrame]) -> int:
        self.saved = data.frame
        self.sha256 = data.sha256
        return len(data.frame)


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

    loaded = TimetableLoader(repository).run(feed, _SHA)

    assert loaded == len(repository.saved)
    assert loaded == 10
    assert repository.sha256 == _SHA
    assert set(repository.saved["service_date"]) == {today, tomorrow}
