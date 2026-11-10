from __future__ import annotations

from collections.abc import Sequence
from typing import override

from psycopg2 import sql

from waw_transit.core import ReadRepository
from waw_transit.core.models import ShapePoint
from waw_transit.database.postgres.cursor import create_provider
from waw_transit.database.postgres.reader import fetch_all, run


def create_trip_shape_reader(
    schema: str = "public",
    trip_shapes_table: str = "gtfs_trip_shapes",
    shapes_table: str = "gtfs_shapes",
) -> ReadRepository[str, Sequence[ShapePoint]]:
    return _TripShapeReader(
        create_provider(), sql.Identifier(schema, trip_shapes_table),
        sql.Identifier(schema, shapes_table), sql.Identifier(schema, "gtfs_versions"),
    )


class _TripShapeReader(ReadRepository[str, Sequence[ShapePoint]]):

    def __init__(
        self,
        provider,
        trip_shapes: sql.Identifier,
        shapes: sql.Identifier,
        versions: sql.Identifier,
    ) -> None:
        self._provider = provider
        self._trip_shapes = trip_shapes
        self._shapes = shapes
        self._versions = versions

    @override
    def load(self, payload: str) -> Sequence[ShapePoint]:
        return run(
            self._provider,
            lambda cur: self._load(cur, payload),
            f"Failed to load shape of trip {payload}",
        )

    def _load(self, cur, trip_id: str) -> Sequence[ShapePoint]:
        rows = fetch_all(
            cur,
            sql.SQL(
                "SELECT points.point_sequence, points.lat, points.lon "
                "FROM {shapes} AS points "
                "JOIN {trip_shapes} AS trips "
                "ON trips.gtfs_version = points.gtfs_version "
                "AND trips.shape_id = points.shape_id "
                "WHERE points.gtfs_version = "
                "(SELECT version_id FROM {versions} WHERE status = 'active') "
                "AND trips.trip_id = %s "
                "ORDER BY points.point_sequence"
            ).format(shapes=self._shapes, trip_shapes=self._trip_shapes, versions=self._versions),
            (trip_id,),
        )
        return tuple(
            ShapePoint(sequence=int(row[0]), lat=float(row[1]), lon=float(row[2]))
            for row in rows
        )
