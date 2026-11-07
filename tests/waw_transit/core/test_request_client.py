import pytest
import requests

from waw_transit.core.request import BaseRequestClient


class _VehicleClient(BaseRequestClient):
    @property
    def _endpoint(self) -> str:
        return "get_ztm_lokalizacja_pojazdow"


def test_when_api_returns_list_then_fetch_data_returns_the_same_list(mocker):
    response = mocker.Mock(status_code=200)
    response.json.return_value = [{"vehicle": "1001"}, {"vehicle": "1002"}]
    post = mocker.patch("waw_transit_pipeline.ingest.request.base.requests.post", return_value=response)

    result = _VehicleClient("api-token").fetch_data()

    assert result == [{"vehicle": "1001"}, {"vehicle": "1002"}]
    post.assert_called_once_with(
        "https://dane.um.warszawa.pl/api/action/get_ztm_lokalizacja_pojazdow",
        headers={"Authorization": "api-token", "Content-Type": "application/json"},
        json={},
        data={},
        timeout=10,
    )


def test_when_api_returns_object_then_fetch_data_returns_it_unchanged(mocker):
    payload = {"result": [{"vehicle": "1001"}]}
    response = mocker.Mock(status_code=200)
    response.json.return_value = payload
    mocker.patch("waw_transit_pipeline.ingest.request.base.requests.post", return_value=response)

    assert _VehicleClient("api-token").fetch_data() == payload


def test_when_api_responds_with_error_then_fetch_data_raises(mocker):
    response = mocker.Mock(status_code=503)
    response.raise_for_status.side_effect = requests.HTTPError("503 Server Error")
    mocker.patch("waw_transit_pipeline.ingest.request.base.requests.post", return_value=response)

    with pytest.raises(requests.HTTPError, match="503"):
        _VehicleClient("api-token").fetch_data()
