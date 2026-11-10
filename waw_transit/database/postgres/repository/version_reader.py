from __future__ import annotations

from typing import override

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import cursor

from waw_transit.core import ParameterlessReadRepository, ProviderParameterlessReadRepository, RepositoryError
from waw_transit.core.ports.repository.provider import Provider
from waw_transit.database.postgres.cursor import create_provider


def create_version_reader(schema: str = "public") -> ParameterlessReadRepository[int]:
    return _VersionReader(create_provider(), schema)


class _VersionReader(ProviderParameterlessReadRepository[cursor, int]):
    def __init__(self, provider: Provider[cursor], schema: str = "public") -> None:
        super().__init__(provider)
        self._versions = sql.Identifier(schema, "gtfs_versions")

    @override
    def load(self) -> int:
        try:
            with self._provider.open() as cur:
                cur.execute(
                    sql.SQL("SELECT version_id FROM {tbl} WHERE status = 'active'")
                    .format(tbl=self._versions)
                )
                row = cur.fetchone()
        except psycopg2.Error as err:
            raise RepositoryError(f"Failed to read the active GTFS version, reason: {err}") from err
        if row is None:
            raise RepositoryError("No active GTFS version in the database")
        return int(row[0])
