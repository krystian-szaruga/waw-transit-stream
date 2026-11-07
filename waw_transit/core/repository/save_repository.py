from __future__ import annotations

from abc import ABC, abstractmethod

from waw_transit.core.repository.repository import Repository


class SaveRepository[Frame, Result](ABC):

    @abstractmethod
    def save(self, frame: Frame) -> Result:
        pass


class ProviderSaveRepository[Resource, Frame, Result](
    Repository[Resource], SaveRepository[Frame, Result], ABC
):
    pass
