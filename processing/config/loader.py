import os
from typing import override

from core import ConfigLoader
from processing.model import VehicleType
from processing.config.config import ProcessingConfig, KafkaConfig, DatabaseConfig


class ProcessingConfigLoader(ConfigLoader[ProcessingConfig]):
    @override
    def _read(self) -> ProcessingConfig:
        self._bootstrap_spark_env()
        return ProcessingConfig(
            kafka=KafkaConfig(
                bootstrap_servers=self._env_reader.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                topics={
                    VehicleType.BUS: self._env_reader.require("KAFKA_TOPIC_BUSES"),
                    VehicleType.TRAM: self._env_reader.require("KAFKA_TOPIC_TRAMS"),
                },
                starting_offsets=self._env_reader.get("KAFKA_STARTING_OFFSETS", "earliest")
            ),
            db=DatabaseConfig(
                db_host=self._env_reader.get("DB_HOST", "127.0.0.1"),
                db_port=self._env_reader.get_int("DB_PORT", 5432),
                db_user=self._env_reader.require("DB_USER"),
                db_password=self._env_reader.require("DB_PASSWORD"),
                db_name=self._env_reader.get("DB_NAME", "warsaw_transit")
            ),
            checkpoint_location=self._env_reader.get("SPARK_CHECKPOINT_LOCATION", "./checkpoints/transit_stream")
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
