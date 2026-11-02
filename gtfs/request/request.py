import requests


class WarsawGtfsDownloader:
    URL = "https://mkuran.pl/gtfs/warsaw.zip"

    def __init__(self, timeout: int = 120):
        self._timeout = timeout

    def download(self) -> bytes:
        response = requests.get(self.URL, timeout=self._timeout)
        response.raise_for_status()
        return response.content
