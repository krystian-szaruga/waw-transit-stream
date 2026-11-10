from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time, timedelta
from typing import override
from zoneinfo import ZoneInfo

from psycopg2 import sql

from waw_transit.core import ReadRepository
from waw_transit.core.models import ScheduleQuery, ScheduledDeparture
from waw_transit.database.postgres.cursor import create_provider
from waw_transit.database.postgres.reader import fetch_all, run


def create_scheduled_departures_reader(
    timezone: str = "Europe/Warsaw",
    schema: str = "public",
    table: str = "static_timetable",
) -> ReadRepository[ScheduleQuery, Sequence[ScheduledDeparture]]:
    return _ScheduledDeparturesReader(create_provider(), ZoneInfo(timezone), schema, table)


class _ScheduledDeparturesReader(ReadRepository[ScheduleQuery, Sequence[ScheduledDeparture]]):

    def __init__(self, provider, timezone: ZoneInfo, schema: str, table: str) -> None:
        self._provider = provider
        self._timezone = timezone
        self._table = sql.Identifier(schema, table)
        self._versions = sql.Identifier(schema, "gtfs_versions")

    @override
    def load(self, payload: ScheduleQuery) -> Sequence[ScheduledDeparture]:
        return run(
            self._provider,
            lambda cur: self._load(cur, payload),
            f"Failed to load scheduled departures for stop {payload.stop_id}",
        )

    def _load(self, cur, payload: ScheduleQuery) -> Sequence[ScheduledDeparture]:
        rows = fetch_all(
            cur,
            sql.SQL(
                "SELECT trip_id, line, stop_sequence, service_date, scheduled_arrival_offset "
                "FROM {tbl} "
                "WHERE gtfs_version = (SELECT version_id FROM {versions} WHERE status = 'active') "
                "AND stop_id = %s AND service_date = ANY(%s) "
                "ORDER BY service_date, scheduled_arrival_offset"
            ).format(tbl=self._table, versions=self._versions),
            (payload.stop_id, list(payload.service_dates)),
        )
        trip_ids = tuple({str(row[0]) for row in rows})
        if not trip_ids:
            return ()
        termini = dict(
            fetch_all(
                cur,
                sql.SQL(
                    "SELECT DISTINCT ON (trip_id) trip_id, stop_name "
                    "FROM {tbl} "
                    "WHERE gtfs_version = (SELECT version_id FROM {versions} WHERE status = 'active') "
                    "AND trip_id = ANY(%s) AND stop_name IS NOT NULL "
                    "ORDER BY trip_id, stop_sequence DESC"
                ).format(tbl=self._table, versions=self._versions),
                (list(trip_ids),),
            )
        )
        return tuple(
            self._to_departure(payload.stop_id, row, termini)
            for row in rows
        )

    def _to_departure(self, stop_id: str, row: tuple, termini: dict) -> ScheduledDeparture:
        trip_id = str(row[0])
        service_date = row[3]
        midnight = datetime.combine(service_date, time.min, tzinfo=self._timezone)
        return ScheduledDeparture(
            stop_id=stop_id,
            trip_id=trip_id,
            line=str(row[1]),
            stop_sequence=int(row[2]),
            direction=str(termini.get(trip_id, "")),
            scheduled=midnight + timedelta(seconds=int(row[4])),
        )
