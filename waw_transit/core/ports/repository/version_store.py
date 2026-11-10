from abc import ABC, abstractmethod


class VersionStore(ABC):

    @abstractmethod
    def save(self, version_id: int) -> None:
        pass
