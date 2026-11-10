from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time, timedelta
from typing import override
from zoneinfo import ZoneInfo

from psycopg2 import sql

from waw_transit.core import ReadRepository
from waw_transit.core.models import TripStopsQuery, TripStopView
from waw_transit.database.postgres.cursor import create_provider
from waw_transit.database.postgres.reader import fetch_all, run


def create_trip_stops_reader(
    timezone: str = "Europe/Warsaw",
    schema: str = "public",
    table: str = "static_timetable",
) -> ReadRepository[TripStopsQuery, Sequence[TripStopView]]:
    return _TripStopsReader(create_provider(), ZoneInfo(timezone), schema, table)


class _TripStopsReader(ReadRepository[TripStopsQuery, Sequence[TripStopView]]):

    def __init__(self, provider, timezone: ZoneInfo, schema: str, table: str) -> None:
        self._provider = provider
        self._timezone = timezone
        self._table = sql.Identifier(schema, table)
        self._versions = sql.Identifier(schema, "gtfs_versions")

    @override
    def load(self, payload: TripStopsQuery) -> Sequence[TripStopView]:
        return run(
            self._provider,
            lambda cur: self._load(cur, payload),
            f"Failed to load stops of trip {payload.trip_id}",
        )

    def _load(self, cur, payload: TripStopsQuery) -> Sequence[TripStopView]:
        rows = fetch_all(
            cur,
            sql.SQL(
                "SELECT stop_sequence, stop_name, scheduled_arrival_offset "
                "FROM {tbl} "
                "WHERE gtfs_version = (SELECT version_id FROM {versions} WHERE status = 'active') "
                "AND trip_id = %s AND service_date = %s "
                "ORDER BY stop_sequence"
            ).format(tbl=self._table, versions=self._versions),
            (payload.trip_id, payload.service_date),
        )
        midnight = datetime.combine(payload.service_date, time.min, tzinfo=self._timezone)
        return tuple(
            TripStopView(
                sequence=int(row[0]),
                name=str(row[1]),
                scheduled=midnight + timedelta(seconds=int(row[2])),
            )
            for row in rows
        )
