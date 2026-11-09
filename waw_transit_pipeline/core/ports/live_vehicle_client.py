from abc import ABC, abstractmethod


class LiveVehicleClient(ABC):

    @abstractmethod
    def fetch(self) -> list[dict[str, str]]:
        pass
