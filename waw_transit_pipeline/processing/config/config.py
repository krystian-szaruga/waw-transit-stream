from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessingConfig:
    checkpoint_location: str
    timezone: str = "Europe/Warsaw"
