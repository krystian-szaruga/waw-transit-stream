import os
from typing import override

from waw_transit.config import ConfigLoader
from waw_transit_pipeline.processing.model import VehicleType
from waw_transit_pipeline.processing.config.config import ProcessingConfig, KafkaConfig


class ProcessingConfigLoader(ConfigLoader[ProcessingConfig]):
    @override
    def _read(self) -> ProcessingConfig:
        self._bootstrap_spark_env()
        return ProcessingConfig(
            kafka=KafkaConfig(
                bootstrap_servers=self._env_reader.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                topics={
                    VehicleType.BUS: self._env_reader.get("KAFKA_TOPIC_BUSES", "buses"),
                    VehicleType.TRAM: self._env_reader.get("KAFKA_TOPIC_TRAMS", "trams"),
                },
                starting_offsets=self._env_reader.get("KAFKA_STARTING_OFFSETS", "earliest")
            ),
            checkpoint_location=self._env_reader.get("SPARK_CHECKPOINT_LOCATION", "./var/checkpoints/transit_stream"),
            timezone=self._env_reader.get("TIMEZONE", "Europe/Warsaw")
        )


    def _bootstrap_spark_env(self):
        os.environ.update(
            **{
                k: v for k, v in {
                    "JAVA_HOME": self._env_reader.get("JAVA_HOME", None),
                    "SPARK_LOCAL_IP": self._env_reader.get("LOCAL_IP", None),
                    "SPARK_LOCAL_HOSTNAME": self._env_reader.get("LOCAL_HOSTNAME", None)
                }.items() if v is not None
            }
        )
