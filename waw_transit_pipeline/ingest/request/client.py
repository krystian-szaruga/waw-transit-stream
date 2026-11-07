import logging
from abc import abstractmethod
from typing import override

from .base import BaseRequestClient


class WarsawTransitClient(BaseRequestClient):
    def __init__(self, api_token: str):
        super().__init__(api_token)

    @property
    @override
    def _payload(self) -> dict[str, int]:
        return {"type": self._get_vehicle_type_id()}

    @property
    @override
    def _endpoint(self) -> str:
        return "get_ztm_lokalizacja_pojazdow"

    @staticmethod
    @abstractmethod
    def _get_vehicle_type_id() -> int:
        """Abstract method that must return strictly the integer ID of the vehicle type."""
        pass


class WarsawBusesClient(WarsawTransitClient):
    @staticmethod
    @override
    def _get_vehicle_type_id() -> int:
        return 1


class WarsawTramsClient(WarsawTransitClient):
    @staticmethod
    @override
    def _get_vehicle_type_id() -> int:
        return 2
