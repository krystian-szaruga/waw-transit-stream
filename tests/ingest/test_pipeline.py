import threading

from ingest.config import ApiConfig, IngestAppConfig, KafkaProducerConfig
from ingest.pipeline import WarsawTransitPipeline


class _StopSignalProducer:
    def __init__(self, name: str, stop_event: threading.Event, executed: list[str]) -> None:
        self._name = name
        self._stop_event = stop_event
        self._executed = executed

    def execute(self) -> None:
        self._executed.append(self._name)
        self._stop_event.set()


class _FakeKafkaClient:
    def __init__(self) -> None:
        self.polls: list[float] = []

    def poll(self, timeout: float) -> None:
        self.polls.append(timeout)


def _config(fetch_interval_seconds: int = 15) -> IngestAppConfig:
    return IngestAppConfig(
        api=ApiConfig("token", fetch_interval_seconds),
        kafka=KafkaProducerConfig("kafka:9092", "client", "buses", "trams"),
    )


def test_when_stop_event_is_already_set_then_no_producer_executes():
    stop_event = threading.Event()
    stop_event.set()
    executed: list[str] = []
    kafka = _FakeKafkaClient()
    pipeline = WarsawTransitPipeline(
        _config(),
        [_StopSignalProducer("bus", stop_event, executed)],
        kafka,
        stop_event,
    )

    pipeline.run()

    assert executed == []
    assert kafka.polls == []


def test_when_a_cycle_runs_then_all_producers_execute_before_polling():
    stop_event = threading.Event()
    executed: list[str] = []
    kafka = _FakeKafkaClient()
    pipeline = WarsawTransitPipeline(
        _config(),
        [
            _StopSignalProducer("bus", stop_event, executed),
            _StopSignalProducer("tram", stop_event, executed),
        ],
        kafka,
        stop_event,
    )

    pipeline.run()

    assert executed == ["bus", "tram"]
    assert kafka.polls == [0]
