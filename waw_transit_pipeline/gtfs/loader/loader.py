import pandas as pd

from waw_transit.core import GtfsPayload, SaveRepository
from waw_transit_pipeline.gtfs.loader.builder import GtfsFeed, ShapeBuilder, TimetableBuilder


class TimetableLoader:
    def __init__(self, repository: SaveRepository[GtfsPayload[pd.DataFrame], int]) -> None:
        self._repository = repository

    def run(self, feed: GtfsFeed, sha256: str) -> int:
        timetable = TimetableBuilder.for_today_and_tomorrow(feed).build()
        trip_shapes, shape_points = ShapeBuilder(feed).build(timetable["trip_id"])
        return self._repository.save(
            GtfsPayload(timetable, trip_shapes, shape_points, sha256)
        )
