import pytest

from waw_transit_pipeline.adapters.kafka.publisher import _KafkaPublisher


class _FakeProducer:
    def __init__(self) -> None:
        self.produced: list[tuple[str, bytes, object]] = []

    def produce(self, topic: str, value: bytes, callback) -> None:
        self.produced.append((topic, value, callback))

    def poll(self, timeout: float) -> None:
        pass

    def flush(self, timeout: float) -> None:
        pass


def test_when_broker_reports_an_error_then_delivery_report_raises():
    producer = _FakeProducer()
    publisher = _KafkaPublisher(producer, "buses")
    publisher.publish({"value": 1})
    _, _, callback = producer.produced[0]

    with pytest.raises(RuntimeError, match="Broker rejected message"):
        callback(RuntimeError("rejected"), object())


def test_when_delivery_succeeds_then_delivery_report_does_not_raise():
    producer = _FakeProducer()
    publisher = _KafkaPublisher(producer, "buses")
    publisher.publish({"value": 1})
    _, _, callback = producer.produced[0]

    assert callback(None, object()) is None


def test_when_publishing_then_the_message_goes_to_the_bound_topic():
    producer = _FakeProducer()
    publisher = _KafkaPublisher(producer, "buses")

    publisher.publish({"value": 1})

    assert producer.produced[0][0] == "buses"


def test_when_publishing_then_the_payload_is_json_encoded():
    producer = _FakeProducer()
    publisher = _KafkaPublisher(producer, "buses")

    publisher.publish({"value": 1})

    assert producer.produced[0][1] == b'{"value":1}'
