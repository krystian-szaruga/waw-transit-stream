from dataclasses import dataclass

from core.config.loader import ConfigLoader


@dataclass(frozen=True)
class _AppConfig:
    token: str
    interval: int


class _AppConfigLoader(ConfigLoader[_AppConfig]):
    def _read(self) -> _AppConfig:
        return _AppConfig(
            token=self._env_reader.require("TOKEN"),
            interval=self._env_reader.get_int("INTERVAL", 15),
        )


def test_when_env_has_required_value_then_load_returns_parsed_config():
    loader = _AppConfigLoader({"TOKEN": "secret"})

    assert loader.load() == _AppConfig(token="secret", interval=15)


def test_when_env_provides_optional_value_then_load_uses_it_over_default():
    loader = _AppConfigLoader({"TOKEN": "secret", "INTERVAL": "30"})

    assert loader.load().interval == 30


def test_when_mapping_and_process_env_disagree_then_load_uses_the_mapping(monkeypatch):
    monkeypatch.setenv("TOKEN", "from-process")

    loader = _AppConfigLoader({"TOKEN": "from-mapping"})

    assert loader.load().token == "from-mapping"
