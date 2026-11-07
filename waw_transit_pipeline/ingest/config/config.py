from dataclasses import dataclass


@dataclass(frozen=True)
class IngestAppConfig:
    fetch_interval_seconds: int
