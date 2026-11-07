import logging
import sys

from waw_transit_pipeline.adapters.kafka import open_kafka_publishers
from waw_transit_pipeline.adapters.ztm import create_buses_client, create_trams_client
from waw_transit_pipeline.ingest import IngestService
from waw_transit_pipeline.ingest.config import IngestConfigLoader


def run_ingest() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    config = IngestConfigLoader().load()
    with open_kafka_publishers() as publishers:
        IngestService(
            config,
            publishers.buses,
            publishers.trams,
            create_buses_client(),
            create_trams_client(),
        ).start()


if __name__ == "__main__":
    run_ingest()
