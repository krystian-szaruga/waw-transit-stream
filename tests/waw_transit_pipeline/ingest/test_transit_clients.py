import pytest

from waw_transit_pipeline.ingest.request import WarsawBusesClient, WarsawTramsClient


@pytest.mark.parametrize(
    ("client_class", "vehicle_type"),
    [(WarsawBusesClient, 1), (WarsawTramsClient, 2)],
)
def test_when_client_fetches_then_payload_carries_its_vehicle_type(
    mocker, client_class, vehicle_type
):
    response = mocker.Mock(status_code=200)
    response.json.return_value = [{"vehicle": "1001"}]
    post = mocker.patch("waw_transit_pipeline.ingest.request.base.requests.post", return_value=response)

    result = client_class("api-token").fetch_data()

    assert result == [{"vehicle": "1001"}]
    post.assert_called_once_with(
        "https://dane.um.warszawa.pl/api/action/get_ztm_lokalizacja_pojazdow",
        headers={"Authorization": "api-token", "Content-Type": "application/json"},
        json={"type": vehicle_type},
        data={},
        timeout=10,
    )
