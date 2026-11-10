from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import override

import orjson
from confluent_kafka import Producer

from waw_transit_pipeline.core.config import KafkaConfigLoader
from waw_transit_pipeline.core.ports import Publisher


@contextmanager
def open_kafka_publishers() -> Iterator[_KafkaPublishers]:
    config = KafkaConfigLoader().load()
    producer = Producer({
        "bootstrap.servers": config.bootstrap_servers,
        "client.id": config.client_id,
        "acks": "all",
        "retries": 5,
        "linger.ms": 20,
    })
    try:
        yield _KafkaPublishers(
            buses=_KafkaPublisher(producer, config.topics["bus"]),
            trams=_KafkaPublisher(producer, config.topics["tram"]),
            versions=_KafkaPublisher(producer, config.version_topic),
        )
    finally:
        producer.flush(5.0)


class _KafkaPublisher(Publisher):
    def __init__(self, producer: Producer, topic: str) -> None:
        self._producer = producer
        self._topic = topic

    @override
    def publish(self, payload: object) -> None:
        self._producer.produce(
            self._topic, orjson.dumps(payload), callback=self._delivery_report
        )

    @override
    def poll(self) -> None:
        self._producer.poll(0)

    @override
    def flush(self, timeout: float) -> None:
        self._producer.flush(timeout)

    @staticmethod
    def _delivery_report(err, msg) -> None:
        if err is not None:
            raise RuntimeError(f"Broker rejected message: {err}, msg: {msg}")


@dataclass(frozen=True)
class _KafkaPublishers:
    buses: Publisher
    trams: Publisher
    versions: Publisher
