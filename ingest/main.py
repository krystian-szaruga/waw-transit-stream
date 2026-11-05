import logging
import sys

from ingest import IngestService


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    IngestService().start()


if __name__ == "__main__":
    main()
