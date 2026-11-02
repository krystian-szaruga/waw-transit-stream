import io
import zipfile
from pathlib import Path

import requests


class WarsawGtfsDownloader:
    URL = "https://mkuran.pl/gtfs/warsaw.zip"
    FILES = (
        "routes.txt",
        "trips.txt",
        "stops.txt",
        "stop_times.txt",
        "calendar_dates.txt",
        "frequencies.txt",
    )

    def __init__(self, target_dir: str = "data/", timeout: int = 120):
        self._target = Path(target_dir)
        self._timeout = timeout

    def download(self) -> Path:
        response = requests.get(self.URL, timeout=self._timeout)
        response.raise_for_status()

        self._target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            available = set(zf.namelist())
            for name in self.FILES:
                if name in available:
                    zf.extract(name, self._target)
        return self._target
