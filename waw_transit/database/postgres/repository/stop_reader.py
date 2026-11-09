from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from psycopg2 import sql
from psycopg2.extensions import cursor

from waw_transit.core import ProviderReadRepository, ReadRepository
from waw_transit.core.models.static_state import StopInfo
from waw_transit.core.ports.repository.provider import Provider
from waw_transit.database.postgres.cursor import create_provider
from waw_transit.database.postgres.reader import fetch_all, fetch_one, run


def create_all_stops_reader(
    schema: str = "public",
    table: str = "static_timetable",
) -> ReadRepository[None, Sequence[StopInfo]]:
    return _AllStopsReader(create_provider(), schema, table)


def create_stop_reader(
    schema: str = "public",
    table: str = "static_timetable",
) -> ReadRepository[str, StopInfo | None]:
    return _StopReader(create_provider(), schema, table)


class _AllStopsReader(ProviderReadRepository[cursor, None, Sequence[StopInfo]]):

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
    def load(self, payload: None = None) -> Sequence[StopInfo]:
        query = sql.SQL(
            "SELECT DISTINCT stop_id, stop_name, stop_lat, stop_lon FROM {tbl} "
            "WHERE gtfs_version = (SELECT version_id FROM {versions} WHERE status = 'active') "
            "AND stop_name IS NOT NULL "
            "ORDER BY stop_name"
        ).format(tbl=self._table, versions=self._versions)
        stops: tuple[StopInfo, ...] = run(
            self._provider,
            lambda cur: tuple(
                _StopRow.from_row(row).to_info()
                for row in fetch_all(cur, query)
            ),
            "Failed to load stops",
        )
        return stops


class _StopReader(ProviderReadRepository[cursor, str, StopInfo | None]):

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
    def load(self, payload: str) -> StopInfo | None:
        query = sql.SQL(
            "SELECT stop_id, stop_name, stop_lat, stop_lon FROM {tbl} "
            "WHERE gtfs_version = (SELECT version_id FROM {versions} WHERE status = 'active') "
            "AND stop_id = %s AND stop_name IS NOT NULL "
            "LIMIT 1"
        ).format(tbl=self._table, versions=self._versions)
        stop: StopInfo | None = run(
            self._provider,
            lambda cur: (
                _StopRow.from_row(row).to_info()
                if (row := fetch_one(cur, query, (payload,))) is not None
                else None
            ),
            f"Failed to load stop {payload}",
        )
        return stop

@dataclass(frozen=True, slots=True)
class _StopRow:
    stop_id: str
    name: str
    lat: float
    lon: float

    @classmethod
    def from_row(cls, row: tuple[str, str, float, float]) -> _StopRow:
        return cls(
            stop_id=str(row[0]),
            name=str(row[1]),
            lat=float(row[2]),
            lon=float(row[3]),
        )

    def to_info(self) -> StopInfo:
        return StopInfo(
            stop_id=self.stop_id,
            name=self.name,
            lat=self.lat,
            lon=self.lon,
        )