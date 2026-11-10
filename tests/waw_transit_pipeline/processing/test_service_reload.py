import threading

from waw_transit.core import RepositoryError
from waw_transit_pipeline.core.ports import VersionWatcher
from waw_transit_pipeline.processing import ProcessingService
from waw_transit_pipeline.processing.config import ProcessingConfig


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


class _Watcher(VersionWatcher):
    def __init__(self, *events: int, stop_after: int | None = None) -> None:
        self._events = list(events)
        self._stop_after = stop_after
        self._stop: threading.Event | None = None
        self.calls = 0
        self.commits = 0

    def bind(self, stop: threading.Event) -> None:
        self._stop = stop

    def next_version(self, timeout_sec: float) -> int | None:
        self.calls += 1
        if self._stop_after is not None and self.calls >= self._stop_after and self._stop is not None:
            self._stop.set()
        if not self._events:
            return None
        return self._events[min(self.calls - 1, len(self._events) - 1)]

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        pass


class _Sink:
    def save(self, frame) -> None:
        pass


class _Reader:
    def load(self, payload=None):
        return None


class _StreamReader:
    def read(self, session):
        return None


class _VersionStore:
    def __init__(self) -> None:
        self.saved: list[int] = []

    def save(self, version_id: int) -> None:
        self.saved.append(version_id)


def _service(watcher: VersionWatcher) -> ProcessingService:
    config = ProcessingConfig(
        checkpoint_location="/tmp/checkpoints",
    )
    return ProcessingService(
        config, _Sink(), _Reader(), _Reader(), watcher, _VersionStore(), _StreamReader()
    )


def test_when_the_active_version_is_unchanged_then_await_keeps_running_until_stop():
    watcher = _Watcher(7, stop_after=3)
    service = _service(watcher)
    watcher.bind(service._stop)
    versions = _Versions(7)
    service._version_reader = versions

    changed = service._await(_Console(), 7)

    assert changed is False
    assert watcher.calls == 3
    assert versions.calls == 3
    assert watcher.commits == 3


def test_when_the_active_version_changes_then_await_returns_immediately():
    watcher = _Watcher(8)
    service = _service(watcher)
    watcher.bind(service._stop)
    service._version_reader = _Versions(8)

    changed = service._await(_Console(), 7)

    assert changed is True
    assert watcher.calls == 1
    assert watcher.commits == 0


def test_when_a_version_event_repeats_the_loaded_version_then_the_event_is_acknowledged():
    watcher = _Watcher(7, stop_after=1)
    service = _service(watcher)
    watcher.bind(service._stop)
    service._version_reader = _Versions(7)

    changed = service._await(_Console(), 7)

    assert changed is False
    assert watcher.commits == 1


def test_when_stop_was_requested_then_await_does_not_wait_for_a_version():
    watcher = _Watcher(7)
    service = _service(watcher)
    service._stop.set()
    versions = _Versions(7)
    service._version_reader = versions

    changed = service._await(_Console(), 7)

    assert changed is False
    assert watcher.calls == 0
    assert versions.calls == 0


def test_when_the_query_went_inactive_then_await_returns_without_changing():
    watcher = _Watcher(7)
    service = _service(watcher)
    versions = _Versions(7)
    service._version_reader = versions

    changed = service._await(_Console(active=False), 7)

    assert changed is False
    assert watcher.calls == 0
    assert versions.calls == 0


def test_when_reading_the_version_fails_then_await_keeps_running_until_stop():
    watcher = _Watcher(7, stop_after=2)
    service = _service(watcher)
    watcher.bind(service._stop)
    versions = _FlakyVersions(then=7)
    service._version_reader = versions

    changed = service._await(_Console(), 7)

    assert changed is False
    assert watcher.commits == 1
