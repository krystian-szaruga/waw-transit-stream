from __future__ import annotations

from abc import ABC

from waw_transit.core.repository.provider import Provider


class Repository[Resource](ABC):
    def __init__(self, provider: Provider[Resource]) -> None:
        self._provider = provider
