import threading

from waw_transit_pipeline.core.ports import Publisher
from waw_transit_pipeline.ingest.config import IngestAppConfig
from waw_transit_pipeline.ingest.pipeline import WarsawTransitPipeline


class _StopSignalPublisher:
    def __init__(self, name: str, stop_event: threading.Event, executed: list[str]) -> None:
        self._name = name
        self._stop_event = stop_event
        self._executed = executed

    def execute(self) -> None:
        self._executed.append(self._name)
        self._stop_event.set()


class _FakePublisher(Publisher):
    def __init__(self) -> None:
        self.polls = 0

    def publish(self, payload: bytes) -> None:
        pass

    def poll(self) -> None:
        self.polls += 1

    def flush(self, timeout: float) -> None:
        pass


def _config(fetch_interval_seconds: int = 15) -> IngestAppConfig:
    return IngestAppConfig(
        fetch_interval_seconds=fetch_interval_seconds,
    )


def test_when_stop_event_is_already_set_then_no_publisher_executes():
    stop_event = threading.Event()
    stop_event.set()
    executed: list[str] = []
    publisher = _FakePublisher()
    pipeline = WarsawTransitPipeline(
        _config(),
        [_StopSignalPublisher("bus", stop_event, executed)],
        publisher,
        stop_event,
    )

    pipeline.run()

    assert executed == []
    assert publisher.polls == 0


def test_when_a_cycle_runs_then_all_publishers_execute_before_polling():
    stop_event = threading.Event()
    executed: list[str] = []
    publisher = _FakePublisher()
    pipeline = WarsawTransitPipeline(
        _config(),
        [
            _StopSignalPublisher("bus", stop_event, executed),
            _StopSignalPublisher("tram", stop_event, executed),
        ],
        publisher,
        stop_event,
    )

    pipeline.run()

    assert executed == ["bus", "tram"]
    assert publisher.polls == 1
