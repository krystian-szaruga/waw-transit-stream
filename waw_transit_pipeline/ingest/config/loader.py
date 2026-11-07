from typing import override

from waw_transit_pipeline.ingest.config import IngestAppConfig, ApiConfig, KafkaProducerConfig
from waw_transit.config import ConfigLoader


class IngestConfigLoader(ConfigLoader[IngestAppConfig]):
    @override
    def _read(self) -> IngestAppConfig:
        return IngestAppConfig(
            api=ApiConfig(
                warsaw_api_token=self._env_reader.require("WARSAW_API_TOKEN"),
                fetch_interval_seconds=self._env_reader.get_int("FETCH_INTERVAL_SECONDS", 15),
            ),
            kafka=KafkaProducerConfig(
                bootstrap_servers=self._env_reader.get("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"),
                client_id=self._env_reader.get("KAFKA_CLIENT_ID", "warsaw-bus-producer"),
                topic_buses=self._env_reader.get("KAFKA_TOPIC_BUSES", "warsaw_transit_buses_raw"),
                topic_trams=self._env_reader.get("KAFKA_TOPIC_TRAMS", "warsaw_transit_trams_raw"),
            ),
        )
