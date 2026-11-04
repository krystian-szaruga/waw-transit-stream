from __future__ import annotations

import io
from datetime import date
from typing import Sequence, override

import pandas as pd
from psycopg2 import sql
from psycopg2.extensions import cursor

from core import Provider
from database.cursor import create_provider
from core import ReadRepository

_COLUMNS = (
    "service_date", "vehicle_type", "line", "brigade", "route_id", "trip_id", "stop_name",
    "stop_id", "stop_sequence", "stop_lat", "stop_lon", "scheduled_arrival_offset",
)
_DTYPES = {
    "vehicle_type": "int16", "line": "string", "brigade": "string", "route_id": "string",
    "stop_name": "string", "trip_id": "string", "stop_id": "string", "stop_sequence": "int32",
    "stop_lat": "float64", "stop_lon": "float64", "scheduled_arrival_offset": "int32",
}


class TimetableReader(ReadRepository[cursor, Sequence[date], pd.DataFrame]):
    """Reads whole service days of `static_timetable` with COPY (cheap even for ~1M rows)."""

    def __init__(self, provider: Provider[cursor], schema: str = "public", table: str = "static_timetable") -> None:
        super().__init__(provider)
        self._table = sql.Identifier(schema, table)

    @override
    def load(self, payload: Sequence[date]) -> pd.DataFrame:
        query = sql.SQL(
            "SELECT {cols} FROM {tbl} WHERE service_date = ANY(ARRAY[{dates}]::date[]) "
            "ORDER BY service_date, trip_id, stop_sequence"
        ).format(
            cols=sql.SQL(", ").join(map(sql.Identifier, _COLUMNS)),
            tbl=self._table,
            dates=sql.SQL(", ").join(sql.Literal(d.isoformat()) for d in payload),
        )
        buffer = io.StringIO()
        with self._provider.open() as cur:
            cur.copy_expert(
                sql.SQL("COPY ({q}) TO STDOUT WITH (FORMAT csv, HEADER true)").format(q=query).as_string(cur),
                buffer,
            )
        buffer.seek(0)
        df = pd.read_csv(buffer, dtype=_DTYPES, keep_default_na=False)
        df["service_date"] = pd.to_datetime(df["service_date"]).dt.date
        return df


def create_timetable_reader(schema: str = "public", table: str = "static_timetable") -> ReadRepository:
    return TimetableReader(create_provider(), schema, table)
