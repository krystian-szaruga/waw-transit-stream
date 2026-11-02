import pandas as pd

from core import SaveRepository
from gtfs.loader.builder import GtfsFeed, TimetableBuilder


class TimetableLoader[RESOURCE]:
    def __init__(self, repository: SaveRepository[RESOURCE, pd.DataFrame, int]) -> None:
        self._repository = repository

    def run(self, feed: GtfsFeed) -> int:
        timetable: pd.DataFrame = TimetableBuilder.for_today_and_tomorrow(feed).build()
        return self._repository.save(timetable)
