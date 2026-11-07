from typing import override

from psycopg2 import sql
from psycopg2.extensions import cursor

from waw_transit.core import ResourceState, ResourceStateRepository
from waw_transit.core.repository.provider import Provider
from waw_transit.database.postgres.cursor import create_provider


def create_state_repository(schema: str = "public") -> ResourceStateRepository[cursor]:
    return _StateRepository(create_provider(), schema)


class _StateRepository(ResourceStateRepository[cursor]):
    def __init__(self, provider: Provider[cursor], schema: str = "public") -> None:
        super().__init__(provider)
        self._table = sql.Identifier(schema, "gtfs_feed_state")

    @override
    def get(self) -> ResourceState:
        with self._provider.open() as cur:
            cur.execute(
                sql.SQL("SELECT etag, last_modified FROM {tbl} WHERE id = 1").format(tbl=self._table)
            )
            etag, last_modified = cur.fetchone()
        return ResourceState(etag=etag, last_modified=last_modified)

    @override
    def put(self, state: ResourceState) -> None:
        with self._provider.open() as cur:
            cur.execute(
                sql.SQL("UPDATE {tbl} SET etag = %s, last_modified = %s WHERE id = 1")
                .format(tbl=self._table),
                (state.etag, state.last_modified),
            )
