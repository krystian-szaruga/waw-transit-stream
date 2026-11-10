from abc import ABC, abstractmethod


class VersionWatcher(ABC):

    @abstractmethod
    def next_version(self, timeout_sec: float) -> int | None:
        pass

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
