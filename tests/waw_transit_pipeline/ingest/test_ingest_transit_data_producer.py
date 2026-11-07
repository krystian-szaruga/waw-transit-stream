import orjson
import pytest

from waw_transit_pipeline.ingest.producer import IngestTransitDataProducer


class _FakeClient:
    def __init__(self, vehicles: list[dict]) -> None:
        self._vehicles = vehicles

    def fetch_data(self) -> list[dict]:
        return self._vehicles


class _FakeKafkaProducer:
    def __init__(self) -> None:
        self.produced: list[tuple[str, bytes, object]] = []

    def produce(self, topic: str, value: bytes, callback) -> None:
        self.produced.append((topic, value, callback))


def test_when_fetch_returns_nothing_then_nothing_is_produced():
    kafka = _FakeKafkaProducer()
    producer = IngestTransitDataProducer(_FakeClient([]), kafka, "buses")

    assert producer.execute() == 0
    assert kafka.produced == []


def test_when_fetch_returns_vehicles_then_each_becomes_one_json_message():
    vehicles = [{"vehicle": "1001", "line": "175"}, {"vehicle": "1002", "line": "9"}]
    kafka = _FakeKafkaProducer()
    producer = IngestTransitDataProducer(_FakeClient(vehicles), kafka, "buses")

    assert producer.execute() == 2
    assert [topic for topic, _, _ in kafka.produced] == ["buses", "buses"]
    assert [orjson.loads(value) for _, value, _ in kafka.produced] == vehicles


def test_when_broker_reports_an_error_then_delivery_callback_raises():
    kafka = _FakeKafkaProducer()
    IngestTransitDataProducer(_FakeClient([{"vehicle": "1001"}]), kafka, "buses").execute()
    _, _, callback = kafka.produced[0]

    with pytest.raises(RuntimeError, match="Broker rejected message"):
        callback(RuntimeError("rejected"), object())


def test_when_delivery_succeeds_then_callback_does_not_raise():
    kafka = _FakeKafkaProducer()
    IngestTransitDataProducer(_FakeClient([{"vehicle": "1001"}]), kafka, "buses").execute()
    _, _, callback = kafka.produced[0]

    assert callback(None, object()) is None
