from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from psycopg2 import sql
from psycopg2.extensions import cursor

from waw_transit.core import ProviderReadRepository, ReadRepository
from waw_transit.core.models.static_state import LineInfo, TripStop
from waw_transit.core.ports.repository.provider import Provider
from waw_transit.database.postgres.cursor import create_provider
from waw_transit.database.postgres.reader import fetch_all, run


def create_trip_reader(
    schema: str = "public",
    table: str = "static_timetable",
) -> ReadRepository[str, Sequence[TripStop]]:
    return _TripReader(create_provider(), schema, table)


def create_lines_reader(
    schema: str = "public",
    table: str = "static_timetable",
) -> ReadRepository[None, Sequence[LineInfo]]:
    return _LinesReader(create_provider(), schema, table)


class _TripReader(ProviderReadRepository[cursor, str, Sequence[TripStop]]):

    def __init__(
        self,
        provider: Provider[cursor],
        schema: str = "public",
        table: str = "static_timetable",
    ) -> None:
        super().__init__(provider)
        self._table = sql.Identifier(schema, table)
        self._versions = sql.Identifier(schema, "gtfs_versions")

    @override
    def load(self, payload: str) -> Sequence[TripStop]:
        query = sql.SQL(
            "SELECT stop_sequence, stop_name FROM {tbl} "
            "WHERE gtfs_version = (SELECT version_id FROM {versions} WHERE status = 'active') "
            "AND trip_id = %s AND stop_name IS NOT NULL "
            "ORDER BY stop_sequence"
        ).format(tbl=self._table, versions=self._versions)
        trip: tuple[TripStop, ...] = run(
            self._provider,
            lambda cur: tuple(
                _TripStopRow.from_row(row).to_model()
                for row in fetch_all(cur, query, (payload,))
            ),
            f"Failed to load trip {payload}",
        )
        return trip


class _LinesReader(ProviderReadRepository[cursor, None, Sequence[LineInfo]]):

    def __init__(
        self,
        provider: Provider[cursor],
        schema: str = "public",
        table: str = "static_timetable",
    ) -> None:
        super().__init__(provider)
        self._table = sql.Identifier(schema, table)
        self._versions = sql.Identifier(schema, "gtfs_versions")

    @override
    def load(self, payload: None = None) -> Sequence[LineInfo]:
        query = sql.SQL(
            "SELECT DISTINCT vehicle_type, line FROM {tbl} "
            "WHERE gtfs_version = (SELECT version_id FROM {versions} WHERE status = 'active') "
            "ORDER BY line"
        ).format(tbl=self._table, versions=self._versions)
        lines: tuple[LineInfo, ...] = run(
            self._provider,
            lambda cur: tuple(
                _LineRow.from_row(row).to_info()
                for row in fetch_all(cur, query)
            ),
            "Failed to load lines",
        )
        return lines


@dataclass(frozen=True, slots=True)
class _TripStopRow:
    sequence: int
    name: str

    @classmethod
    def from_row(cls, row: tuple[int, str]) -> _TripStopRow:
        return cls(sequence=int(row[0]), name=str(row[1]))

    def to_model(self) -> TripStop:
        return TripStop(sequence=self.sequence, name=self.name)


@dataclass(frozen=True, slots=True)
class _LineRow:
    name: str
    vehicle_type: int

    @classmethod
    def from_row(cls, row: tuple[int, str]) -> _LineRow:
        return cls(name=str(row[1]), vehicle_type=int(row[0]))

    def to_info(self) -> LineInfo:
        return LineInfo(name=self.name, vehicle_type=self.vehicle_type)