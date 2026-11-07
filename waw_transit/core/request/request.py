import functools
import logging
import time
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger("RequestMonitoring")


def _log_api_request(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        method_name = func.__name__
        logger.info(f"Executing API request via method: '{method_name}'...")
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        if isinstance(result, list):
            logger.info(f"Method '{method_name}' completed in {duration:.2f}s. Fetched {len(result)} items.")
        else:
            logger.info(f"Method '{method_name}' completed in {duration:.2f}s.")
        return result
    return wrapper


class BaseRequestClient(ABC):
    def __init__(self, api_token: str):
        self._base_api = "https://dane.um.warszawa.pl/api/action/"
        self._headers = {
            "Authorization": f"{api_token}",
            "Content-Type": "application/json"
        }

    @_log_api_request
    def fetch_data(self) -> list[dict[str, str]]:
        response = requests.post(
            self._url,
            headers=self._headers,
            json=self._payload,
            data = self._data,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
            return data
        response.raise_for_status()
        return []

    @property
    def _payload(self) -> dict:
        return {}

    @property
    def _data(self) -> dict:
        return {}

    @property
    @abstractmethod
    def _endpoint(self) -> str:
        pass

    @property
    def _url(self) -> str:
        return self._base_api + self._endpoint
