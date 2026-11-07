from dataclasses import dataclass


@dataclass(frozen=True)
class Payload[Frame]:
    frame: Frame
    sha256: str


@dataclass(frozen=True)
class ResourceState:
    etag: str | None = None
    last_modified: str | None = None
