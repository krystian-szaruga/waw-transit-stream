import logging
import sys

from waw_transit_pipeline.ingest import IngestService
from waw_transit_pipeline.ingest.config import IngestConfigLoader


def run_ingest() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    IngestService(IngestConfigLoader().load()).start()


if __name__ == "__main__":
    run_ingest()
