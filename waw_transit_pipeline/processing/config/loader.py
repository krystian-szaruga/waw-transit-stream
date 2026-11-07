from typing import override

from waw_transit.config import ConfigLoader
from waw_transit_pipeline.processing.config.config import ProcessingConfig


class ProcessingConfigLoader(ConfigLoader[ProcessingConfig]):
    @override
    def _read(self) -> ProcessingConfig:
        return ProcessingConfig(
            checkpoint_location=self._env_reader.get("SPARK_CHECKPOINT_LOCATION", "./var/checkpoints/transit_stream"),
            timezone=self._env_reader.get("TIMEZONE", "Europe/Warsaw"),
        )
