from __future__ import annotations

import io
from datetime import date
from typing import Sequence, override

import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import cursor

from waw_transit.core import ProviderReadRepository, ReadRepository, RepositoryError
from waw_transit.core.ports.repository.provider import Provider
from waw_transit.database.postgres.cursor import create_provider

_COLUMNS = (
    "service_date", "vehicle_type", "line", "brigade", "route_id", "trip_id", "stop_name",
    "stop_id", "stop_sequence", "stop_lat", "stop_lon", "scheduled_arrival_offset",
)
_DTYPES = {
    "vehicle_type": "int16", "line": "string", "brigade": "string", "route_id": "string",
    "stop_name": "string", "trip_id": "string", "stop_id": "string", "stop_sequence": "int32",
    "stop_lat": "float64", "stop_lon": "float64", "scheduled_arrival_offset": "int32",
}


def create_timetable_reader(schema: str = "public", table: str = "static_timetable") -> ReadRepository[Sequence[date], tuple[pd.DataFrame, int]]:
    return _TimetableReader(create_provider(), schema, table)


class _TimetableReader(ProviderReadRepository[cursor, Sequence[date], tuple[pd.DataFrame, int]]):
    """Reads whole service days of `static_timetable` with COPY (cheap even for ~1M rows)."""

    def __init__(self, provider: Provider[cursor], schema: str = "public", table: str = "static_timetable") -> None:
        super().__init__(provider)
        self._table = sql.Identifier(schema, table)
        self._versions = sql.Identifier(schema, "gtfs_versions")

    @override
    def load(self, payload: Sequence[date]) -> tuple[pd.DataFrame, int]:
        buffer = io.StringIO()
        try:
            with self._provider.open() as cur:
                version_id = self._active_version(cur)
                query = sql.SQL(
                    "SELECT {cols} FROM {tbl} WHERE service_date = ANY(ARRAY[{dates}]::date[]) "
                    "AND gtfs_version = {version} "
                    "ORDER BY service_date, trip_id, stop_sequence"
                ).format(
                    cols=sql.SQL(", ").join(map(sql.Identifier, _COLUMNS)),
                    tbl=self._table,
                    version=sql.Literal(version_id),
                    dates=sql.SQL(", ").join(sql.Literal(d.isoformat()) for d in payload),
                )
                cur.copy_expert(
                    sql.SQL("COPY ({q}) TO STDOUT WITH (FORMAT csv, HEADER true)").format(q=query).as_string(cur),
                    buffer,
                )
        except psycopg2.Error as err:
            raise RepositoryError(f"Failed to load the timetable, reason: {err}") from err
        buffer.seek(0)
        df = pd.read_csv(buffer, dtype=_DTYPES, keep_default_na=False)
        df["service_date"] = pd.to_datetime(df["service_date"]).dt.date
        return df, version_id

    def _active_version(self, cur) -> int:
        cur.execute(
            sql.SQL("SELECT version_id FROM {tbl} WHERE status = 'active'")
            .format(tbl=self._versions)
        )
        row = cur.fetchone()
        if row is None:
            raise RepositoryError("No active GTFS version in the database")
        return int(row[0])
