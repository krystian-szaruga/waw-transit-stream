from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import override

import redis

from waw_transit.config import ConfigLoader
from waw_transit.core.repository.provider import Provider


class RedisSession(Provider[redis.Redis]):
    _SOCKET_TIMEOUT_SEC = 1.0
    _MAX_CONNECTIONS = 10

    def __init__(self) -> None:
        self._config: _RedisConfig = _RedisConfigLoader().load()
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


@dataclass(frozen=True)
class _RedisConfig:
    host: str = "127.0.0.1"
    port: int = 6379
    password: str = ""
    db: int = 0


class _RedisConfigLoader(ConfigLoader[_RedisConfig]):
    @override
    def _read(self) -> _RedisConfig:
        return _RedisConfig(
            host=self._env_reader.get("REDIS_HOST", "127.0.0.1"),
            port=self._env_reader.get_int("REDIS_PORT", 6379),
            password=self._env_reader.get("REDIS_PASSWORD", ""),
            db=self._env_reader.get_int("REDIS_DB", 0),
        )
