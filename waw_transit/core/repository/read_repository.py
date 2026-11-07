from __future__ import annotations

from abc import abstractmethod

from waw_transit.core.repository.repository import Repository


class ReadRepository[Resource, Payload, Result](Repository[Resource]):

    @abstractmethod
    def load(self, payload: Payload) -> Result:
        pass
