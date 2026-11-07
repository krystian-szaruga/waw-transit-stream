from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, override

import redis

from waw_transit.core.repository.provider import Provider

if TYPE_CHECKING:
    from waw_transit_pipeline.processing.config.config import RedisConfig


class RedisSession(Provider[redis.Redis]):
    _SOCKET_TIMEOUT_SEC = 1.0
    _MAX_CONNECTIONS = 10

    def __init__(self, config: RedisConfig) -> None:
        self._config = config
        self._pool = redis.ConnectionPool(
            host=self._config.host,
            port=self._config.port,
            password=self._config.password,
            db=self._config.db,
            socket_connect_timeout=self._SOCKET_TIMEOUT_SEC,
            socket_timeout=self._SOCKET_TIMEOUT_SEC,
            decode_responses=True,
            max_connections=self._MAX_CONNECTIONS,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._pool.disconnect()

    @contextmanager
    @override
    def open(self) -> Generator[redis.Redis, None, None]:
        client = redis.Redis(connection_pool=self._pool)
        try:
            yield client
        finally:
            client.close()
