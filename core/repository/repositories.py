from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class Provider[Resource](ABC):

    @abstractmethod
    def open(self) -> AbstractContextManager[Resource]:
        pass

class Repository[Resource](ABC):
    def __init__(self, provider: Provider[Resource]) -> None:
        self._provider = provider



class SaveRepository[Resource, Payload, Result](Repository[Resource]):

    @abstractmethod
    def save(self, data: Payload) -> Result:
        pass


class ReadRepository[Resource, Payload, Result](Repository[Resource]):

    @abstractmethod
    def load(self, payload: Payload) -> Result:
        pass