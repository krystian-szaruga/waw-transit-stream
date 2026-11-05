from typing import override

from psycopg2 import sql
from psycopg2.extensions import cursor

from core import Provider, ReadRepository, ResourceState, SaveRepository
from database.cursor import create_provider


def create_state_repository(schema: str = "public") -> SaveRepository[cursor, ResourceState, None]:
    return _StateRepository(create_provider(), schema)


class _StateRepository(SaveRepository[cursor, ResourceState, None], ReadRepository[cursor, None, ResourceState]):
    def __init__(self, provider: Provider[cursor], schema: str = "public") -> None:
        super().__init__(provider)
        self._table = sql.Identifier(schema, "gtfs_feed_state")

    @override
    def load(self, payload: None = None) -> ResourceState:
        with self._provider.open() as cur:
            cur.execute(
                sql.SQL("SELECT etag, last_modified FROM {tbl} WHERE id = 1").format(tbl=self._table)
            )
            etag, last_modified = cur.fetchone()
        return ResourceState(etag=etag, last_modified=last_modified)

    @override
    def save(self, data: ResourceState) -> None:
        with self._provider.open() as cur:
            cur.execute(
                sql.SQL("UPDATE {tbl} SET etag = %s, last_modified = %s WHERE id = 1")
                .format(tbl=self._table),
                (data.etag, data.last_modified),
            )
