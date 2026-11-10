import io
from datetime import date
from typing import override

import pandas as pd
from psycopg2 import sql
from psycopg2._psycopg import cursor

from waw_transit.core import GtfsPayload, ProviderSaveRepository, SaveRepository
from waw_transit.core.ports.repository.provider import Provider
from waw_transit.database.postgres.cursor import create_provider


def create_timetable_writer(
        schema: str = "public",
        table: str = "static_timetable",
        versions_table: str = "gtfs_versions",
        trip_shapes_table: str = "gtfs_trip_shapes",
        shape_points_table: str = "gtfs_shapes",
) -> SaveRepository[GtfsPayload[pd.DataFrame], int]:
    return _TimetableWriter(
        create_provider(), schema, table, versions_table, trip_shapes_table, shape_points_table
    )


class _TimetableWriter(ProviderSaveRepository[cursor, GtfsPayload[pd.DataFrame], int]):
    _KEEP_RETIRED = 3

    def __init__(
            self,
            provider: Provider[cursor],
            schema: str = "public",
            table: str = "static_timetable",
            versions_table: str = "gtfs_versions",
            trip_shapes_table: str = "gtfs_trip_shapes",
            shape_points_table: str = "gtfs_shapes",
    ) -> None:
        super().__init__(provider)
        self._table = sql.Identifier(schema, table)
        self._versions = sql.Identifier(schema, versions_table)
        self._trip_shapes = sql.Identifier(schema, trip_shapes_table)
        self._shape_points = sql.Identifier(schema, shape_points_table)

    @override
    def save(self, frame: GtfsPayload[pd.DataFrame]) -> int:
        with self._provider.open() as cur:
            known = self._version_id(cur, frame.sha256)
            if known is not None:
                return known
            version_id = self._insert_version(cur, frame.sha256)
            self._copy_frame(cur, self._table, frame.timetable, version_id)
            self._copy_frame(cur, self._trip_shapes, frame.trip_shapes, version_id)
            self._copy_frame(cur, self._shape_points, frame.shape_points, version_id)
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
        export = data.assign(gtfs_version=version_id)
        if "service_date" in export.columns:
            export = export.assign(service_date=export["service_date"].map(date.isoformat))
        export = export[["gtfs_version", *data.columns]]
        buffer = io.StringIO()
        export.to_csv(buffer, index=False, header=False)
        buffer.seek(0)
        return buffer

    def _copy_frame(self, cur: cursor, table: sql.Composable, frame: pd.DataFrame, version_id: int) -> None:
        self._copy(
            cur,
            table,
            self._to_csv_buffer(frame, version_id),
            ["gtfs_version", *frame.columns],
        )

    def _copy(self, cur: cursor, table: sql.Composable, buffer: io.StringIO, columns: list[str]) -> int:
        cur.copy_expert(
            sql.SQL("COPY {tbl} ({cols}) FROM STDIN WITH (FORMAT csv)")
            .format(tbl=table, cols=self._identifiers(columns))
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
        for table in (self._shape_points, self._trip_shapes, self._table):
            cur.execute(
                sql.SQL("DELETE FROM {tbl} WHERE gtfs_version NOT IN ({kept})")
                .format(tbl=table, kept=kept),
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
