import pandas as pd

from core import SaveRepository, Payload
from gtfs.loader.builder import GtfsFeed, TimetableBuilder


class TimetableLoader[RESOURCE]:
    def __init__(self, repository: SaveRepository[RESOURCE, pd.DataFrame, int]) -> None:
        self._repository = repository

    def run(self, feed: GtfsFeed, sha256: str) -> int:
        return self._repository.save(
            Payload(
                TimetableBuilder.for_today_and_tomorrow(feed).build(), sha256
            )
        )
  