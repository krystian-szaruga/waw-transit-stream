from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from dataclasses import dataclass

class Provider[Resource](ABC):

    @abstractmethod
    def open(self) -> AbstractContextManager[Resource]:
        pass

class Repository[Resource](ABC):
    def __init__(self, provider: Provider[Resource]) -> None:
        self._provider = provider


class SaveRepository[Resource, Frame, Result](Repository[Resource]):

    @abstractmethod
    def save(self, data: Payload[Frame]) -> Result:
        pass


class ReadRepository[Resource, Payload, Result](Repository[Resource]):

    @abstractmethod
    def load(self, payload: Payload) -> Result:
        pass


class StateRepository[Resource](ABC):
    def __init__(self, provider: Provider[Resource]) -> None:
        self._provider = provider

    @abstractmethod
    def get(self) -> ResourceState:
        pass

    @abstractmethod
    def put(self, state: ResourceState) -> None:
        pass


@dataclass(frozen=True)
class Payload[Frame]:
    frame: Frame
    sha256: str


@dataclass(frozen=True)
class ResourceState:
    etag: str | None = None
    last_modified: str | None = None
