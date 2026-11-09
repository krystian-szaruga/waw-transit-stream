import hashlib

import pytest
import requests

from waw_transit_pipeline.adapters.gtfs import create_gtfs_downloader

_ETAG = '"dmmu0miyvc3z-1oxn28"'
_LAST_MODIFIED = "Wed, 04 Nov 2026 23:57:17 GMT"


def test_when_download_succeeds_then_it_returns_the_content_with_its_sha256(mocker):
    content = b"zip-content"
    response = mocker.Mock(
        content=content,
        status_code=200,
        headers={"ETag": _ETAG, "Last-Modified": _LAST_MODIFIED},
    )
    get = mocker.patch("waw_transit_pipeline.adapters.gtfs.downloader.requests.get", return_value=response)

    downloaded = create_gtfs_downloader(timeout=5).download()

    assert downloaded.content == content
    assert downloaded.sha256 == hashlib.sha256(content).hexdigest()
    assert downloaded.etag == _ETAG
    assert downloaded.last_modified == _LAST_MODIFIED
    get.assert_called_once_with(
        "https://mkuran.pl/gtfs/warsaw.zip",
        timeout=5,
        headers={"User-Agent": "waw-transit-stream/0.1"},
    )
    response.raise_for_status.assert_called_once_with()


def test_when_validators_are_known_then_they_are_sent_as_conditional_headers(mocker):
    response = mocker.Mock(content=b"zip-content", status_code=200, headers={})
    get = mocker.patch("waw_transit_pipeline.adapters.gtfs.downloader.requests.get", return_value=response)

    create_gtfs_downloader(timeout=5).download(etag=_ETAG, last_modified=_LAST_MODIFIED)

    get.assert_called_once_with(
        "https://mkuran.pl/gtfs/warsaw.zip",
        timeout=5,
        headers={
            "User-Agent": "waw-transit-stream/0.1",
            "If-None-Match": _ETAG,
            "If-Modified-Since": _LAST_MODIFIED,
        },
    )


def test_when_the_feed_is_unchanged_then_download_returns_none(mocker):
    response = mocker.Mock(content=b"", status_code=304, headers={})
    mocker.patch("waw_transit_pipeline.adapters.gtfs.downloader.requests.get", return_value=response)

    assert create_gtfs_downloader().download(etag=_ETAG) is None
    response.raise_for_status.assert_not_called()


def test_when_download_fails_then_the_http_error_is_raised(mocker):
    response = mocker.Mock(content=b"", status_code=404, headers={})
    response.raise_for_status.side_effect = requests.HTTPError("404 Client Error")
    mocker.patch("waw_transit_pipeline.adapters.gtfs.downloader.requests.get", return_value=response)

    with pytest.raises(requests.HTTPError, match="404"):
        create_gtfs_downloader().download()
