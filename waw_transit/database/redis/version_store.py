from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import override

import redis

from waw_transit.core import (
    ParameterlessReadRepository,
    ProviderParameterlessReadRepository,
    RepositoryError,
    VersionStore,
)
from waw_transit.database.redis.session import RedisSession

logger = logging.getLogger(__name__)


@contextmanager
def open_version_store() -> Iterator[VersionStore]:
    with RedisSession() as session:
        yield create_version_store(session)


def create_version_store(session: RedisSession) -> VersionStore:
    return _RedisVersionStore(session)


def create_active_version_reader() -> ParameterlessReadRepository[int | None]:
    return _RedisActiveVersion(RedisSession())


class _RedisVersionStore(VersionStore):
    _KEY = "gtfs:active_version"

    def __init__(self, session: RedisSession) -> None:
        self._session = session

    def save(self, version_id: int) -> None:
        try:
            with self._session.open() as client:
                client.set(self._KEY, version_id)
        except redis.RedisError as err:
            logger.exception(f"Failed to write the active GTFS version to Redis, reason: {err}")


class _RedisActiveVersion(ProviderParameterlessReadRepository[redis.Redis, int | None]):
    _KEY = "gtfs:active_version"

    @override
    def load(self) -> int | None:
        try:
            with self._provider.open() as client:
                value = client.get(self._KEY)
        except redis.RedisError as err:
            raise RepositoryError(f"Failed to read the active GTFS version, reason: {err}") from err
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

