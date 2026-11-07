import pytest

from waw_transit_pipeline.ingest.config import IngestAppConfig, ApiConfig, KafkaProducerConfig
from waw_transit_pipeline.ingest.pipeline.log_pipeline_cycle import log_pipeline_cycle


class _Subject:
    def __init__(self, fetch_interval_seconds: int) -> None:
        self._config = IngestAppConfig(
            api=ApiConfig("token", fetch_interval_seconds),
            kafka=KafkaProducerConfig("kafka:9092", "client", "buses", "trams"),
        )

    @log_pipeline_cycle
    def cycle(self) -> None:
        pass


class _FailingSubject(_Subject):
    @log_pipeline_cycle
    def cycle(self) -> None:
        raise RuntimeError("boom")


def test_when_cycle_is_faster_than_interval_then_remaining_time_is_returned(mocker):
    mocker.patch("waw_transit_pipeline.ingest.pipeline.log_pipeline_cycle.time.time", side_effect=[100.0, 102.0])

    assert _Subject(15).cycle() == 13.0


def test_when_cycle_is_slower_than_interval_then_minimum_sleep_is_returned(mocker):
    mocker.patch("waw_transit_pipeline.ingest.pipeline.log_pipeline_cycle.time.time", side_effect=[100.0, 120.0])

    assert _Subject(15).cycle() == 0.1


def test_when_cycle_crashes_then_the_error_is_reraised(mocker):
    mocker.patch("waw_transit_pipeline.ingest.pipeline.log_pipeline_cycle.time.time", side_effect=[100.0, 102.0])

    with pytest.raises(RuntimeError, match="boom"):
        _FailingSubject(15).cycle()
