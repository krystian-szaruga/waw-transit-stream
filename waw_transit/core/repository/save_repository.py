from __future__ import annotations

from abc import abstractmethod

from waw_transit.core.models import Payload
from waw_transit.core.repository.repository import Repository


class SaveRepository[Resource, Frame, Result](Repository[Resource]):

    @abstractmethod
    def save(self, data: Payload[Frame]) -> Result:
        pass
