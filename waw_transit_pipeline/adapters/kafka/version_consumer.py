from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import override

from confluent_kafka import Consumer, KafkaError, KafkaException, Message

from waw_transit_pipeline.core.config import KafkaConfig
from waw_transit_pipeline.core.ports import VersionWatcher

logger = logging.getLogger(__name__)

_POLL_SEC = 1.0


@contextmanager
def open_version_watcher(config: KafkaConfig) -> Iterator[VersionWatcher]:
    consumer = Consumer({
        "bootstrap.servers": config.bootstrap_servers,
        "client.id": config.client_id,
        "group.id": f"{config.client_id}-gtfs-version",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    watcher = _KafkaVersionWatcher(consumer, config.version_topic)
    try:
        yield watcher
    finally:
        watcher.close()


class _KafkaVersionWatcher(VersionWatcher):
    def __init__(self, consumer: Consumer, topic: str) -> None:
        self._consumer = consumer
        self._topic = topic
        self._consumer.subscribe([topic])

    @override
    def next_version(self, timeout_sec: float) -> int | None:
        deadline = time.monotonic() + timeout_sec
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            message = self._poll(min(_POLL_SEC, remaining))
            if message is None:
                continue
            if message.error() is not None:
                self._log_error(message)
                continue
            version_id = _parse_version(message)
            if version_id is not None:
                return version_id
            logger.warning("Ignoring malformed version message on topic %s", self._topic)

    @override
    def commit(self) -> None:
        self._consumer.commit(asynchronous=False)

    @override
    def close(self) -> None:
        self._consumer.close()

    @staticmethod
    def _log_error(message: Message) -> None:
        error = message.error()
        if error is not None and error.code() != KafkaError._PARTITION_EOF:
            logger.error("Kafka version consumer error: %s", error)

    def _poll(self, timeout_sec: float) -> Message | None:
        try:
            return self._consumer.poll(timeout_sec)
        except KafkaException as err:
            logger.error("Kafka version consumer failed to poll: %s", err)
            return None


def _parse_version(message: Message) -> int | None:
    payload = message.value()
    if payload is None:
        return None
    try:
        data = json.loads(payload)
        return int(data["version_id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
