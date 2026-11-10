from waw_transit_pipeline.core.ports import Publisher
from waw_transit_pipeline.ingest.publisher import IngestTransitPublisher


class _FakeClient:
    def __init__(self, vehicles: list[dict]) -> None:
        self._vehicles = vehicles

    def fetch(self) -> list[dict]:
        return self._vehicles


class _FakePublisher(Publisher):
    def __init__(self) -> None:
        self.produced: list[object] = []

    def publish(self, payload: object) -> None:
        self.produced.append(payload)

    def poll(self) -> None:
        pass

    def flush(self, timeout: float) -> None:
        pass


def test_when_fetch_returns_nothing_then_nothing_is_published():
    publisher = _FakePublisher()
    subject = IngestTransitPublisher(_FakeClient([]), publisher)

    assert subject.execute() == 0
    assert publisher.produced == []


def test_when_fetch_returns_vehicles_then_each_becomes_one_json_message():
    vehicles = [{"vehicle": "1001", "line": "175"}, {"vehicle": "1002", "line": "9"}]
    publisher = _FakePublisher()
    subject = IngestTransitPublisher(_FakeClient(vehicles), publisher)

    assert subject.execute() == 2
    assert publisher.produced == vehicles
