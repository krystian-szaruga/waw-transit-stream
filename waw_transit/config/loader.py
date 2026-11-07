from abc import ABC, abstractmethod
from typing import Generic, Mapping, Optional, TypeVar

from dotenv import load_dotenv

from waw_transit.config.env_reader import EnvReader

T = TypeVar("T")


class ConfigLoader(ABC, Generic[T]):
    def __init__(self, env: Optional[Mapping[str, str]] = None) -> None:
        self._env_reader = EnvReader(env)

    def load(self) -> T:
        load_dotenv()
        return self._read()

    @abstractmethod
    def _read(self) -> T:
        pass
