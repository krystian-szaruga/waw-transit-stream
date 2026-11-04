import pytest
import requests

from gtfs.request import WarsawGtfsDownloader


def test_when_download_succeeds_then_it_returns_the_response_bytes(mocker):
    response = mocker.Mock(content=b"zip-content")
    get = mocker.patch("gtfs.request.request.requests.get", return_value=response)

    assert WarsawGtfsDownloader(timeout=5).download() == b"zip-content"
    get.assert_called_once_with(WarsawGtfsDownloader.URL, timeout=5)
    response.raise_for_status.assert_called_once_with()


def test_when_download_fails_then_the_http_error_is_raised(mocker):
    response = mocker.Mock(content=b"")
    response.raise_for_status.side_effect = requests.HTTPError("404 Client Error")
    mocker.patch("gtfs.request.request.requests.get", return_value=response)

    with pytest.raises(requests.HTTPError, match="404"):
        WarsawGtfsDownloader().download()
