import pytest

from core.config.env_reader import ConfigError, EnvReader


def test_when_key_present_then_require_returns_its_value():
    reader = EnvReader({"DB_USER": "transit"})

    assert reader.require("DB_USER") == "transit"


def test_when_key_missing_then_require_raises_config_error():
    reader = EnvReader({})

    with pytest.raises(ConfigError, match="MISSING"):
        reader.require("MISSING")


def test_when_key_is_empty_then_require_raises_config_error():
    reader = EnvReader({"TOKEN": ""})

    with pytest.raises(ConfigError, match="TOKEN"):
        reader.require("TOKEN")


def test_when_key_present_then_get_returns_stored_value():
    reader = EnvReader({"DB_HOST": "db.internal"})

    assert reader.get("DB_HOST", "127.0.0.1") == "db.internal"


def test_when_key_missing_then_get_returns_default():
    reader = EnvReader({})

    assert reader.get("DB_HOST", "127.0.0.1") == "127.0.0.1"


def test_when_value_is_integer_text_then_get_int_returns_int():
    reader = EnvReader({"DB_PORT": "6432"})

    assert reader.get_int("DB_PORT", 5432) == 6432


def test_when_key_missing_then_get_int_returns_default():
    reader = EnvReader({})

    assert reader.get_int("DB_PORT", 5432) == 5432


def test_when_value_is_not_integer_then_get_int_raises_config_error():
    reader = EnvReader({"DB_PORT": "six thousand"})

    with pytest.raises(ConfigError, match="DB_PORT"):
        reader.get_int("DB_PORT", 5432)


def test_when_no_mapping_given_then_reader_uses_process_environment(monkeypatch):
    monkeypatch.setenv("DB_NAME", "warsaw_transit")

    assert EnvReader().require("DB_NAME") == "warsaw_transit"
