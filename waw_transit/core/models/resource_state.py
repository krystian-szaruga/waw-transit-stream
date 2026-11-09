from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceState:
    etag: str | None = None
    last_modified: str | None = None
