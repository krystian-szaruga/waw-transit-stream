from __future__ import annotations

import hashlib
from typing import override

import requests

from waw_transit_pipeline.core.models import Gtfs
from waw_transit_pipeline.core.ports import GtfsDownloader


class _MkuranGtfsDownloader(GtfsDownloader):
    URL = "https://mkuran.pl/gtfs/warsaw.zip"
    USER_AGENT = "waw-transit-stream/0.1"

    def __init__(self, timeout: int = 120):
        self._timeout = timeout

    @override
    def download(
            self,
            etag: str | None = None,
            last_modified: str | None = None,
    ) -> Gtfs | None:
        headers = {"User-Agent": self.USER_AGENT}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        response = requests.get(self.URL, timeout=self._timeout, headers=headers)
        if response.status_code == 304:
            return None
        response.raise_for_status()
        return Gtfs(
            content=response.content,
            sha256=hashlib.sha256(response.content).hexdigest(),
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
        )


def create_gtfs_downloader(timeout: int = 120) -> GtfsDownloader:
    return _MkuranGtfsDownloader(timeout)
