from __future__ import annotations

from dataclasses import dataclass
from typing import override

from waw_transit.config import ConfigLoader


@dataclass(frozen=True)
class KafkaConfig:
    bootstrap_servers: str
    client_id: str
    starting_offsets: str
    topics: dict[str, str]


class KafkaConfigLoader(ConfigLoader[KafkaConfig]):
    @override
    def _read(self) -> KafkaConfig:
        return KafkaConfig(
            bootstrap_servers=self._env_reader.get("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"),
            client_id=self._env_reader.get("KAFKA_CLIENT_ID", "warsaw-transit"),
            starting_offsets=self._env_reader.get("KAFKA_STARTING_OFFSETS", "latest"),
            topics={
                "bus": self._env_reader.get("KAFKA_TOPIC_BUSES", "warsaw_transit_buses_raw"),
                "tram": self._env_reader.get("KAFKA_TOPIC_TRAMS", "warsaw_transit_trams_raw"),
            },
        )
