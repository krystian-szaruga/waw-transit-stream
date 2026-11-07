import pandas as pd

from waw_transit.core import SaveRepository, Payload
from waw_transit_pipeline.gtfs.loader.builder import GtfsFeed, TimetableBuilder


class TimetableLoader[RESOURCE]:
    def __init__(self, repository: SaveRepository[RESOURCE, pd.DataFrame, int]) -> None:
        self._repository = repository

    def run(self, feed: GtfsFeed, sha256: str) -> int:
        return self._repository.save(
            Payload(
                TimetableBuilder.for_today_and_tomorrow(feed).build(), sha256
            )
        )
  