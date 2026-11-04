import logging

import pytest

from core.timed.timed import timed


def test_when_block_finishes_then_logs_label_and_elapsed_time(caplog, mocker):
    mocker.patch("core.timed.timed.time.perf_counter", side_effect=[10.0, 12.5])
    caplog.set_level(logging.INFO, logger="core.timed.timed")

    with timed("build feed"):
        pass

    assert "build feed: 2.5s" in caplog.messages


def test_when_block_raises_then_logs_elapsed_time_and_rethrows(caplog, mocker):
    mocker.patch("core.timed.timed.time.perf_counter", side_effect=[5.0, 7.0])
    caplog.set_level(logging.INFO, logger="core.timed.timed")

    with pytest.raises(RuntimeError, match="boom"):
        with timed("load zip"):
            raise RuntimeError("boom")

    assert "load zip: 2.0s" in caplog.messages
