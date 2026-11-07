import io
from datetime import date
from typing import override

import pandas as pd
from psycopg2 import sql
from psycopg2._psycopg import cursor

from waw_transit.core import SaveRepository, Payload
from waw_transit.core.repository.provider import Provider
from waw_transit.database.postgres.cursor import create_provider


def create_timetable_writer(
        schema: str = "public",
        table: str = "static_timetable",
        versions_table: str = "gtfs_versions",
) -> SaveRepository[cursor, pd.DataFrame, int]:
    return _TimetableWriter(create_provider(), schema, table, versions_table)


class _TimetableWriter(SaveRepository[cursor, pd.DataFrame, int]):
    _KEEP_RETIRED = 3

    def __init__(
            self,
            provider: Provider[cursor],
            schema: str = "public",
            table: str = "static_timetable",
            versions_table: str = "gtfs_versions",
    ) -> None:
        super().__init__(provider)
        self._table = sql.Identifier(schema, table)
        self._versions = sql.Identifier(schema, versions_table)

    @override
    def save(self, data: Payload[pd.DataFrame]) -> int:
        with self._provider.open() as cur:
            known = self._version_id(cur, data.sha256)
            if known is not None:
                return known
            version_id = self._insert_version(cur, data.sha256)
            self._copy(cur, self._to_csv_buffer(data.frame, version_id), ["gtfs_version", *data.frame.columns])
            self._activate(cur, version_id)
            self._prune(cur, self._KEEP_RETIRED)
            return version_id

    def _version_id(self, cur, sha256: str) -> int | None:
        cur.execute(
            sql.SQL("SELECT version_id FROM {tbl} WHERE sha256 = %s").format(tbl=self._versions),
            (sha256,),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def _insert_version(self, cur, sha256: str) -> int:
        cur.execute(
            sql.SQL("INSERT INTO {tbl} (sha256) VALUES (%s) RETURNING version_id")
            .format(tbl=self._versions),
            (sha256,),
        )
        return cur.fetchone()[0]

    @staticmethod
    def _to_csv_buffer(data: pd.DataFrame, version_id: int) -> io.StringIO:
        export = data.assign(
            gtfs_version=version_id,
            service_date=data["service_date"].map(date.isoformat),
        )[["gtfs_version", *data.columns]]
        buffer = io.StringIO()
        export.to_csv(buffer, index=False, header=False)
        buffer.seek(0)
        return buffer

    def _copy(self, cur, buffer: io.StringIO, columns: list[str]) -> int:
        cur.copy_expert(
            sql.SQL("COPY {tbl} ({cols}) FROM STDIN WITH (FORMAT csv)")
            .format(tbl=self._table, cols=self._identifiers(columns))
            .as_string(cur),
            buffer,
        )
        return cur.rowcount

    def _activate(self, cur, version_id: int) -> None:
        cur.execute(
            sql.SQL("UPDATE {tbl} SET status = 'retired' WHERE status = 'active'")
            .format(tbl=self._versions)
        )
        cur.execute(
            sql.SQL("UPDATE {tbl} SET status = 'active' WHERE version_id = %s")
            .format(tbl=self._versions),
            (version_id,),
        )

    def _prune(self, cur, keep_retired: int) -> None:
        kept = self._kept_versions()
        cur.execute(
            sql.SQL("DELETE FROM {timetable} WHERE gtfs_version NOT IN ({kept})")
            .format(timetable=self._table, kept=kept),
            (keep_retired,),
        )
        cur.execute(
            sql.SQL("DELETE FROM {versions} WHERE version_id NOT IN ({kept})")
            .format(versions=self._versions, kept=kept),
            (keep_retired,),
        )

    def _kept_versions(self) -> sql.Composed:
        return sql.SQL(
            "SELECT version_id FROM {tbl} WHERE status = 'active' UNION "
            "SELECT version_id FROM {tbl} WHERE version_id IN ("
            "SELECT version_id FROM {tbl} WHERE status = 'retired' "
            "ORDER BY loaded_at DESC LIMIT %s)"
        ).format(tbl=self._versions)

    @staticmethod
    def _identifiers(names) -> sql.Composed:
        return sql.SQL(", ").join(map(sql.Identifier, names))
