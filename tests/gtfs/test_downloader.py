import hashlib

import pytest
import requests

from gtfs.request import WarsawGtfsDownloader

_ETAG = '"dmmu0miyvc3z-1oxn28"'
_LAST_MODIFIED = "Wed, 04 Nov 2026 23:57:17 GMT"


def test_when_download_succeeds_then_it_returns_the_content_with_its_sha256(mocker):
    content = b"zip-content"
    response = mocker.Mock(
        content=content,
        status_code=200,
        headers={"ETag": _ETAG, "Last-Modified": _LAST_MODIFIED},
    )
    get = mocker.patch("gtfs.request.request.requests.get", return_value=response)

    downloaded = WarsawGtfsDownloader(timeout=5).download()

    assert downloaded.content == content
    assert downloaded.sha256 == hashlib.sha256(content).hexdigest()
    assert downloaded.etag == _ETAG
    assert downloaded.last_modified == _LAST_MODIFIED
    get.assert_called_once_with(
        WarsawGtfsDownloader.URL,
        timeout=5,
        headers={"User-Agent": WarsawGtfsDownloader.USER_AGENT},
    )
    response.raise_for_status.assert_called_once_with()


def test_when_validators_are_known_then_they_are_sent_as_conditional_headers(mocker):
    response = mocker.Mock(content=b"zip-content", status_code=200, headers={})
    get = mocker.patch("gtfs.request.request.requests.get", return_value=response)

    WarsawGtfsDownloader(timeout=5).download(etag=_ETAG, last_modified=_LAST_MODIFIED)

    get.assert_called_once_with(
        WarsawGtfsDownloader.URL,
        timeout=5,
        headers={
            "User-Agent": WarsawGtfsDownloader.USER_AGENT,
            "If-None-Match": _ETAG,
            "If-Modified-Since": _LAST_MODIFIED,
        },
    )


def test_when_the_feed_is_unchanged_then_download_returns_none(mocker):
    response = mocker.Mock(content=b"", status_code=304, headers={})
    mocker.patch("gtfs.request.request.requests.get", return_value=response)

    assert WarsawGtfsDownloader().download(etag=_ETAG) is None
    response.raise_for_status.assert_not_called()


def test_when_download_fails_then_the_http_error_is_raised(mocker):
    response = mocker.Mock(content=b"", status_code=404, headers={})
    response.raise_for_status.side_effect = requests.HTTPError("404 Client Error")
    mocker.patch("gtfs.request.request.requests.get", return_value=response)

    with pytest.raises(requests.HTTPError, match="404"):
        WarsawGtfsDownloader().download()
