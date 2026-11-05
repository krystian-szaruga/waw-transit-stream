import argparse
import logging

from gtfs import TimetableSync


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=1800)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    sync = TimetableSync(args.interval)
    if args.watch:
        sync.watch()
    else:
        sync.run()


if __name__ == "__main__":
    main()
