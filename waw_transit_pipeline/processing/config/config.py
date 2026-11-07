from __future__ import annotations

from dataclasses import dataclass, field

from waw_transit_pipeline.processing.model.models import VehicleType


@dataclass(frozen=True)
class KafkaConfig:
    bootstrap_servers: str
    topics: dict[VehicleType, str] = field(default_factory=dict)
    starting_offsets: str = "latest"


@dataclass(frozen=True)
class DatabaseConfig:
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_user: str = "de_user"
    db_password: str = "de_password"
    db_name: str = "warsaw_transit"


@dataclass(frozen=True)
class RedisConfig:
    host: str = "127.0.0.1"
    port: int = 6379
    password: str = ""
    db: int = 0


@dataclass(frozen=True)
class ProcessingConfig:
    kafka: KafkaConfig
    db: DatabaseConfig
    redis: RedisConfig
    checkpoint_location: str
    max_event_age_minutes: int = 10
    write_partitions: int = 2
    timezone: str = "Europe/Warsaw"
