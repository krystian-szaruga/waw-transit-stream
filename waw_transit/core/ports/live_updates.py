from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from waw_transit.core.models import VehicleSnapshot


class LiveVehicleStream(ABC):

    @abstractmethod
    def stream(self) -> AsyncIterator[VehicleSnapshot]:
        pass
