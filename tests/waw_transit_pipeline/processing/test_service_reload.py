import threading

from waw_transit.core import RepositoryError
from waw_transit_pipeline.processing import ProcessingService
from waw_transit_pipeline.processing.config import KafkaConfig, ProcessingConfig


class _StoppingEvent(threading.Event):
    def __init__(self, after: int) -> None:
        super().__init__()
        self._after = after
        self._waits = 0

    def wait(self, timeout=None) -> bool:
        self._waits += 1
        if self._waits >= self._after:
            self.set()
        return self.is_set()


class _Console:
    def __init__(self, active: bool = True) -> None:
        self.isActive = active


class _Versions:
    def __init__(self, *values: int) -> None:
        self._values = list(values)
        self.calls = 0

    def load(self) -> int:
        self.calls += 1
        value = self._values[min(self.calls - 1, len(self._values) - 1)]
        return value


class _FlakyVersions:
    def __init__(self, then: int) -> None:
        self._then = then
        self._failed = False

    def load(self) -> int:
        if not self._failed:
            self._failed = True
            raise RepositoryError("database is down")
        return self._then


class _Sink:
    def save(self, frame) -> None:
        pass


class _Reader:
    def load(self, payload=None):
        return None


def _service(stop_after: int) -> ProcessingService:
    config = ProcessingConfig(
        kafka=KafkaConfig(bootstrap_servers="localhost:9092"),
        checkpoint_location="/tmp/checkpoints",
    )
    service = ProcessingService(config, _Sink(), _Reader(), _Reader())
    service._stop = _StoppingEvent(stop_after)
    return service


def test_when_the_active_version_is_unchanged_then_await_keeps_running_until_stop():
    service = _service(stop_after=3)

    changed = service._await(_Console(), _Versions(7), 7)

    assert changed is False
    assert service._stop._waits == 3


def test_when_the_active_version_changes_then_await_returns_immediately():
    service = _service(stop_after=100)

    changed = service._await(_Console(), _Versions(8), 7)

    assert changed is True
    assert service._stop._waits == 0


def test_when_stop_was_requested_then_await_does_not_poll_for_a_version():
    service = _service(stop_after=1)
    service._stop.set()
    versions = _Versions(7)

    changed = service._await(_Console(), versions, 7)

    assert changed is False
    assert versions.calls == 0


def test_when_the_query_went_inactive_then_await_returns_without_changing():
    service = _service(stop_after=100)
    versions = _Versions(7)

    changed = service._await(_Console(active=False), versions, 7)

    assert changed is False
    assert versions.calls == 0


def test_when_reading_the_version_fails_then_await_keeps_running_until_stop():
    service = _service(stop_after=2)

    changed = service._await(_Console(), _FlakyVersions(then=7), 7)

    assert changed is False
    assert service._stop._waits == 2
