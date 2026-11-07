from __future__ import annotations

from abc import ABC, abstractmethod

from waw_transit.core.repository.repository import Repository


class ReadRepository[Payload, Result](ABC):

    @abstractmethod
    def load(self, payload: Payload) -> Result:
        pass


class ProviderReadRepository[Resource, Payload, Result](
    Repository[Resource], ReadRepository[Payload, Result], ABC
):
    pass
