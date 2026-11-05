import pytest

from core import ResourceState
from gtfs import main as gtfs_main
from gtfs.request import GtfsDownload

_SHA = "a" * 64
_ETAG = '"dmmu0miyvc3z-1oxn28"'
_LAST_MODIFIED = "Wed, 04 Nov 2026 23:57:17 GMT"


def _patch_state(mocker) -> object:
    repository = mocker.patch("gtfs.main.create_state_repository").return_value
    repository.get.return_value = ResourceState(etag=_ETAG, last_modified=_LAST_MODIFIED)
    return repository


def test_when_the_feed_changed_then_run_once_loads_it_and_stores_the_new_state(mocker):
    state = _patch_state(mocker)
    mocker.patch("gtfs.main.WarsawGtfsDownloader").return_value.download.return_value = (
        GtfsDownload(b"zip", _SHA, _ETAG, _LAST_MODIFIED)
    )
    mocker.patch("gtfs.main.GtfsFeed.from_zip", return_value="feed")
    mocker.patch("gtfs.main.create_timetable_writer", return_value="writer")
    loader = mocker.patch("gtfs.main.TimetableLoader").return_value
    loader.run.return_value = 7

    assert gtfs_main.run_once() == 7
    loader.run.assert_called_once_with("feed", _SHA)
    state.put.assert_called_once_with(ResourceState(_ETAG, _LAST_MODIFIED))


def test_when_the_feed_is_unchanged_then_run_once_returns_none_and_saves_nothing(mocker):
    state = _patch_state(mocker)
    downloader = mocker.patch("gtfs.main.WarsawGtfsDownloader").return_value
    downloader.download.return_value = None
    loader = mocker.patch("gtfs.main.TimetableLoader")

    assert gtfs_main.run_once() is None
    downloader.download.assert_called_once_with(_ETAG, _LAST_MODIFIED)
    state.put.assert_not_called()
    loader.assert_not_called()


def test_when_watching_then_it_loads_again_after_sleeping_the_interval(mocker):
    mocker.patch("gtfs.main.run_once", side_effect=[7, 8])
    intervals: list[int] = []

    def _sleep(seconds: int) -> None:
        intervals.append(seconds)
        if len(intervals) == 2:
            raise KeyboardInterrupt

    mocker.patch("gtfs.main.time.sleep", side_effect=_sleep)

    with pytest.raises(KeyboardInterrupt):
        gtfs_main.main(["--watch"])

    assert intervals == [1800, 1800]


def test_when_not_watching_then_it_runs_once_and_returns(mocker):
    mocker.patch("gtfs.main.run_once", return_value=7)
    sleep = mocker.patch("gtfs.main.time.sleep")

    gtfs_main.main([])

    sleep.assert_not_called()
