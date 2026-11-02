import io
from datetime import date
from typing import override

import pandas as pd
from psycopg2 import sql
from psycopg2._psycopg import cursor

from core import Provider, SaveRepository
from database.cursor import create_provider


class _TimetableWriter(SaveRepository[cursor, pd.DataFrame, int]):
    _PK_COLUMNS = ("service_date", "trip_id", "stop_sequence")
    _INDEX_COLUMNS = ("service_date", "vehicle_type", "line", "brigade")

    def __init__(
            self,
            provider: Provider[cursor],
            schema: str = "public",
            table: str = "static_timetable",
    ) -> None:
        super().__init__(provider)
        self._table = sql.Identifier(schema, table)
        self._index = sql.Identifier(schema, "idx_timetable_matching")
        self._index_name = sql.Identifier("idx_timetable_matching")
        self._pk = sql.Identifier(f"{table}_pkey")

    @override
    def save(self, data: pd.DataFrame) -> int:
        dates = sorted(data["service_date"].unique())
        buffer = self._to_csv_buffer(data, dates)
        with self._provider.open() as cur:
            self._delete_obsolete(cur, dates)
            self._drop_indexes(cur)
            inserted = self._copy(cur, buffer, list(data.columns))
            self._create_indexes(cur)
            return inserted

    @staticmethod
    def _to_csv_buffer(data: pd.DataFrame, dates: list[date]) -> io.StringIO:
        export = data.assign(
            service_date=data["service_date"].map({d: d.isoformat() for d in dates})
        )
        buffer = io.StringIO()
        export.to_csv(buffer, index=False, header=False)
        buffer.seek(0)
        return buffer

    def _delete_obsolete(self, cur, dates: list[date]) -> None:
        cur.execute(
            sql.SQL("DELETE FROM {tbl} WHERE service_date = ANY(%s) OR service_date < %s")
            .format(tbl=self._table),
            (dates, dates[0]),
        )

    def _drop_indexes(self, cur) -> None:
        cur.execute(sql.SQL("DROP INDEX IF EXISTS {idx}").format(idx=self._index))
        cur.execute(
            sql.SQL("ALTER TABLE {tbl} DROP CONSTRAINT IF EXISTS {pk}")
            .format(tbl=self._table, pk=self._pk)
        )

    def _copy(self, cur, buffer: io.StringIO, columns: list[str]) -> int:
        cur.copy_expert(
            sql.SQL("COPY {tbl} ({cols}) FROM STDIN WITH (FORMAT csv)")
            .format(tbl=self._table, cols=self._identifiers(columns))
            .as_string(cur),
            buffer,
        )
        return cur.rowcount

    def _create_indexes(self, cur) -> None:
        cur.execute(
            sql.SQL("ALTER TABLE {tbl} ADD PRIMARY KEY ({cols})")
            .format(tbl=self._table, cols=self._identifiers(self._PK_COLUMNS))
        )
        cur.execute(
            sql.SQL("CREATE INDEX {idx} ON {tbl} ({cols})")
            .format(
                idx=self._index_name,
                tbl=self._table,
                cols=self._identifiers(self._INDEX_COLUMNS),
            )
        )

    @staticmethod
    def _identifiers(names) -> sql.Composed:
        return sql.SQL(", ").join(map(sql.Identifier, names))


def create_timetable_writer(
        schema: str = "public",
        table: str = "static_timetable"
) -> SaveRepository[cursor, pd.DataFrame, int]:
    return _TimetableWriter(create_provider(), schema, table)
