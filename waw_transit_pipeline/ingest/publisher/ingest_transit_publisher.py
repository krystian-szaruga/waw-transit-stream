import orjson

from waw_transit_pipeline.core.ports import LiveVehicleClient, Publisher
from waw_transit_pipeline.ingest.publisher.log_publishing import log_publishing


class IngestTransitPublisher:
    def __init__(self, client: LiveVehicleClient, publisher: Publisher):
        self._client = client
        self._publisher = publisher

    @log_publishing
    def execute(self) -> int:
        if not (vehicles := self._client.fetch()): return 0
        for v in vehicles:
            self._publisher.publish(orjson.dumps(v))
        return len(vehicles)
