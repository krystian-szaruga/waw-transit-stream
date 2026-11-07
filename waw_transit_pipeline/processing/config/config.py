from __future__ import annotations

from dataclasses import dataclass, field

from waw_transit_pipeline.processing.model.models import VehicleType


@dataclass(frozen=True)
class KafkaConfig:
    bootstrap_servers: str
    topics: dict[VehicleType, str] = field(default_factory=dict)
    starting_offsets: str = "latest"


@dataclass(frozen=True)
class ProcessingConfig:
    kafka: KafkaConfig
    checkpoint_location: str
    max_event_age_minutes: int = 10
    write_partitions: int = 2
    timezone: str = "Europe/Warsaw"
