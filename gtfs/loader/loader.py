from pathlib import Path

import pandas as pd

from core import SaveRepository
from gtfs.loader.builder import GtfsFeed, TimetableBuilder


class TimetableLoader[RESOURCE]:
    def __init__(self, repository: SaveRepository[RESOURCE, pd.DataFrame, int]) -> None:
        self._repository = repository

    def run(self, feed_dir: Path) -> int:
        feed: GtfsFeed = GtfsFeed.from_directory(feed_dir)
        timetable: pd.DataFrame = TimetableBuilder.for_today_and_tomorrow(feed).build()
        return self._repository.save(timetable)