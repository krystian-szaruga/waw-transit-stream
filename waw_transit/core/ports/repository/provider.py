from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class Provider[Resource](ABC):

    @abstractmethod
    def open(self) -> AbstractContextManager[Resource]:
        pass
