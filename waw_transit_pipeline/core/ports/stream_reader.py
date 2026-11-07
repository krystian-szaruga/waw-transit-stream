from abc import ABC, abstractmethod


class StreamReader[Session, Frame](ABC):

    @abstractmethod
    def read(self, session: Session) -> Frame:
        pass
