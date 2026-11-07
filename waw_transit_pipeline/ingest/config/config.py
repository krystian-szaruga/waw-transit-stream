from dataclasses import dataclass


@dataclass(frozen=True)
class ApiConfig:
    warsaw_api_token: str
    fetch_interval_seconds: int

@dataclass(frozen=True)
class KafkaProducerConfig:
    bootstrap_servers: str
    client_id: str
    topic_buses: str
    topic_trams: str

@dataclass(frozen=True)
class IngestAppConfig:
    api: ApiConfig
    kafka: KafkaProducerConfig
