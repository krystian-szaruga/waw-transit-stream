from abc import ABC, abstractmethod


class Publisher(ABC):

    @abstractmethod
    def publish(self, payload: bytes) -> None:
        pass

    @abstractmethod
    def poll(self) -> None:
        pass

    @abstractmethod
    def flush(self, timeout: float) -> None:
        pass
