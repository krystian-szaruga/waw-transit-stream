import pytest

from waw_transit.config.env_reader import ConfigError
from waw_transit_pipeline.ingest.config import IngestConfigLoader


def test_when_only_the_token_is_given_then_ingest_defaults_are_used():
    config = IngestConfigLoader({"WARSAW_API_TOKEN": "token"}).load()

    assert config.api.fetch_interval_seconds == 15
    assert config.kafka.bootstrap_servers == "127.0.0.1:9092"
    assert config.kafka.client_id == "warsaw-bus-producer"
    assert config.kafka.topic_buses == "warsaw_transit_buses_raw"
    assert config.kafka.topic_trams == "warsaw_transit_trams_raw"


def test_when_env_overrides_defaults_then_custom_values_are_loaded():
    config = IngestConfigLoader(
        {
            "WARSAW_API_TOKEN": "secret",
            "FETCH_INTERVAL_SECONDS": "30",
            "KAFKA_BOOTSTRAP_SERVERS": "kafka:9093",
            "KAFKA_CLIENT_ID": "warsaw-producer",
            "KAFKA_TOPIC_BUSES": "buses",
            "KAFKA_TOPIC_TRAMS": "trams",
        }
    ).load()

    assert config.api.warsaw_api_token == "secret"
    assert config.api.fetch_interval_seconds == 30
    assert config.kafka.bootstrap_servers == "kafka:9093"
    assert config.kafka.client_id == "warsaw-producer"
    assert config.kafka.topic_buses == "buses"
    assert config.kafka.topic_trams == "trams"


def test_when_token_is_missing_then_load_raises_config_error():
    with pytest.raises(ConfigError, match="WARSAW_API_TOKEN"):
        IngestConfigLoader({}).load()


def test_when_interval_is_not_a_number_then_load_raises_config_error():
    with pytest.raises(ConfigError, match="FETCH_INTERVAL_SECONDS"):
        IngestConfigLoader(
            {"WARSAW_API_TOKEN": "token", "FETCH_INTERVAL_SECONDS": "soon"}
        ).load()
