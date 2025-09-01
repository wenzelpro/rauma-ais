# tests/test_basic.py
import json
from app import app

def test_health():
    with app.test_client() as c:
        res = c.get("/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"

def test_default_area_load():
    with open("map.geojson", "r", encoding="utf-8") as f:
        gj = json.load(f)
    assert "type" in gj


def test_data_endpoint():
    with app.test_client() as c:
        res = c.get("/data")
        assert res.status_code == 200
        data = res.get_json()
        assert "rows" in data
        assert isinstance(data["rows"], list)
