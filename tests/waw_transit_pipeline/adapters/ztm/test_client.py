import pytest

from waw_transit_pipeline.adapters.ztm import create_buses_client, create_trams_client


@pytest.mark.parametrize(
    ("create_client", "vehicle_type"),
    [(create_buses_client, 1), (create_trams_client, 2)],
)
def test_when_client_fetches_then_payload_carries_its_vehicle_type(
    mocker, create_client, vehicle_type
):
    response = mocker.Mock(status_code=200)
    response.json.return_value = [{"vehicle": "1001"}]
    post = mocker.patch(
        "waw_transit_pipeline.adapters.ztm.client.requests.post",
        return_value=response,
    )

    result = create_client("api-token").fetch()

    assert result == [{"vehicle": "1001"}]
    post.assert_called_once_with(
        "https://dane.um.warszawa.pl/api/action/get_ztm_lokalizacja_pojazdow",
        headers={"Authorization": "api-token", "Content-Type": "application/json"},
        json={"type": vehicle_type},
        timeout=10,
    )
