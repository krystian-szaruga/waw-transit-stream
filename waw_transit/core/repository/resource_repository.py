from __future__ import annotations

from abc import ABC, abstractmethod

from waw_transit.core.models import ResourceState
from waw_transit.core.repository.provider import Provider


class ResourceStateRepository[Resource](ABC):
    def __init__(self, provider: Provider[Resource]) -> None:
        self._provider = provider

    @abstractmethod
    def get(self) -> ResourceState:
        pass

    @abstractmethod
    def put(self, state: ResourceState) -> None:
        pass
