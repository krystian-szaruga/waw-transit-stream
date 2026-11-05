import orjson
from confluent_kafka import Producer

from ingest.producer.log_kafka_streaming import log_kafka_streaming
from ingest.request import WarsawTransitClient


class IngestTransitDataProducer:
    def __init__(self, client: WarsawTransitClient, producer: Producer, topic: str):
        self._client = client
        self._producer = producer
        self._topic = topic

    @log_kafka_streaming
    def execute(self) -> int:
        if not (vehicles := self._client.fetch_data()): return 0
        for v in vehicles:
            self._producer.produce(
                self._topic, orjson.dumps(v), callback=self._delivery_report
            )
        return len(vehicles)

    @staticmethod
    def _delivery_report(err, msg):
        if err is not None:
            raise RuntimeError(f"Broker rejected message: {err}, msg: {msg}")
