from __future__ import annotations

from abc import ABC, abstractmethod

from waw_transit.core.ports.repository.repository import Repository


class ReadRepository[Payload, Result](ABC):

    @abstractmethod
    def load(self, payload: Payload) -> Result:
        pass


class ParameterlessReadRepository[Result](ABC):

    @abstractmethod
    def load(self) -> Result:
        pass


class ProviderReadRepository[Resource, Payload, Result](
    Repository[Resource], ReadRepository[Payload, Result], ABC
):
    pass


class ProviderParameterlessReadRepository[Resource, Result](
    Repository[Resource], ParameterlessReadRepository[Result], ABC
):
    pass
