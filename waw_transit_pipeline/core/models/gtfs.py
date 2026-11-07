from dataclasses import dataclass


@dataclass(frozen=True)
class Gtfs:
    content: bytes
    sha256: str
    etag: str | None = None
    last_modified: str | None = None
