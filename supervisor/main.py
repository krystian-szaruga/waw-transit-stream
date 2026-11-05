import logging
import sys

from supervisor import Supervisor


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    Supervisor().run()


if __name__ == "__main__":
    main()
