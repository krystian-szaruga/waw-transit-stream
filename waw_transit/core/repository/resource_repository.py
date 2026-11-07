from __future__ import annotations

from abc import ABC, abstractmethod

from waw_transit.core.models import ResourceState
from waw_transit.core.repository.repository import Repository


class ResourceStateRepository(ABC):

    @abstractmethod
    def get(self) -> ResourceState:
        pass

    @abstractmethod
    def put(self, state: ResourceState) -> None:
        pass


class ProviderResourceStateRepository[Resource](
    Repository[Resource], ResourceStateRepository, ABC
):
    pass
