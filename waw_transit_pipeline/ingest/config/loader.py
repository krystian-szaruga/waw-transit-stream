from typing import override

from waw_transit.config import ConfigLoader
from waw_transit_pipeline.ingest.config import IngestAppConfig


class IngestConfigLoader(ConfigLoader[IngestAppConfig]):
    @override
    def _read(self) -> IngestAppConfig:
        return IngestAppConfig(
            fetch_interval_seconds=self._env_reader.get_int("FETCH_INTERVAL_SECONDS", 15),
        )
