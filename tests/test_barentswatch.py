# tests/test_barentswatch.py
from barentswatch import BarentsWatchClient


class FakeResponse:
    status_code = 200

    def json(self):
        return [
            {
                "mmsi": 123456789,
                "name": "Test Ship",
                "latitude": 1.0,
                "longitude": 2.0,
                "msgtime": "2023-01-01T00:00:00Z",
                "shipType": "Cargo",
                "destination": "Somewhere",
                "lengthoverall": 150,
            }
        ]


class FakeSession:
    def post(self, url, headers=None, json=None, timeout=None):
        return FakeResponse()


def test_fetch_latest_combined_includes_destination_and_lengthoverall():
    client = BarentsWatchClient(
        client_id=None,
        client_secret=None,
        static_access_token="token",
        session=FakeSession(),
    )
    features = client.fetch_latest_combined([123456789])
    assert features[0]["destination"] == "Somewhere"
    assert features[0]["lengthoverall"] == 150
