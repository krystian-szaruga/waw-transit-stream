import argparse
import glob
import pstats
from pathlib import Path


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--sort", default="cumulative", choices=["cumulative", "tottime"])
    args = parser.parse_args()

    paths = sorted(glob.glob(str(args.directory / "*.pstats")))
    if not paths:
        print(f"no .pstats files in {args.directory}")
        return

    print(f"profiles: {len(paths)}")
    _merge(paths).strip_dirs().sort_stats(args.sort).print_stats(args.top)


def _merge(paths: list[str]) -> pstats.Stats:
    stats = pstats.Stats(paths[0])
    for path in paths[1:]:
        stats.add(path)
    return stats


if __name__ == "__main__":
    _main()
