import pytest

from waw_transit.config.env_reader import ConfigError
from waw_transit_pipeline.ingest.config import IngestConfigLoader


def test_when_no_env_is_given_then_default_interval_is_used():
    config = IngestConfigLoader({}).load()

    assert config.fetch_interval_seconds == 15


def test_when_env_overrides_interval_then_custom_value_is_loaded():
    config = IngestConfigLoader({"FETCH_INTERVAL_SECONDS": "30"}).load()

    assert config.fetch_interval_seconds == 30


def test_when_interval_is_not_a_number_then_load_raises_config_error():
    with pytest.raises(ConfigError, match="FETCH_INTERVAL_SECONDS"):
        IngestConfigLoader({"FETCH_INTERVAL_SECONDS": "soon"}).load()
