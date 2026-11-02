import os
from typing import Mapping, Optional


class ConfigError(RuntimeError):
    """Raised when the environment configuration is missing or invalid."""


class EnvReader:
    def __init__(self, env: Optional[Mapping[str, str]] = None) -> None:
        self._env = os.environ if env is None else env

    def require(self, key: str) -> str:
        value = self._env.get(key)
        if not value:
            raise ConfigError(f"Missing required environment variable: {key}")
        return value

    def get(self, key: str, default: str) -> str:
        return self._env.get(key, default)

    def get_int(self, key: str, default: int) -> int:
        raw = self._env.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"{key} must be an integer, got {raw!r}") from None
