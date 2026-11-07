from __future__ import annotations

import functools
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import override

import requests

from waw_transit.config import ConfigLoader
from waw_transit_pipeline.core.ports import LiveVehicleClient

logger = logging.getLogger("RequestMonitoring")


def _log_api_request(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        logger.info(
            "Method '%s' completed in %.2fs. Fetched %d items.",
            func.__name__,
            time.time() - start_time,
            len(result),
        )
        return result
    return wrapper


class _ZtmLiveVehicleClient(LiveVehicleClient, ABC):
    _BASE_API = "https://dane.um.warszawa.pl/api/action/"
    _ENDPOINT = "get_ztm_lokalizacja_pojazdow"
    _TIMEOUT_SEC = 10

    def __init__(self, api_token: str | None = None) -> None:
        token = api_token or _ZtmConfigLoader().load().api_token
        self._headers = {
            "Authorization": f"{token}",
            "Content-Type": "application/json",
        }

    @override
    @_log_api_request
    def fetch(self) -> list[dict[str, str]]:
        response = requests.post(
            self._BASE_API + self._ENDPOINT,
            headers=self._headers,
            json={"type": self._get_vehicle_type_id()},
            timeout=self._TIMEOUT_SEC,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else [data]

    @staticmethod
    @abstractmethod
    def _get_vehicle_type_id() -> int:
        pass


class _ZtmBusesClient(_ZtmLiveVehicleClient):
    @staticmethod
    @override
    def _get_vehicle_type_id() -> int:
        return 1


class _ZtmTramsClient(_ZtmLiveVehicleClient):
    @staticmethod
    @override
    def _get_vehicle_type_id() -> int:
        return 2


@dataclass(frozen=True)
class _ZtmConfig:
    api_token: str


class _ZtmConfigLoader(ConfigLoader[_ZtmConfig]):
    @override
    def _read(self) -> _ZtmConfig:
        return _ZtmConfig(api_token=self._env_reader.require("WARSAW_API_TOKEN"))


def create_buses_client(api_token: str | None = None) -> LiveVehicleClient:
    return _ZtmBusesClient(api_token)


def create_trams_client(api_token: str | None = None) -> LiveVehicleClient:
    return _ZtmTramsClient(api_token)
