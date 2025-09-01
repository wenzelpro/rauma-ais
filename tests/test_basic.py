# tests/test_basic.py
import json

import app as app_module
from app import app
from sqlalchemy.exc import SQLAlchemyError

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


def test_data_endpoint_debug_detail(monkeypatch):
    app.debug = True

    class FailingEngine:
        def connect(self):
            raise SQLAlchemyError("Boom!")

    monkeypatch.setattr(app_module, "_engine", FailingEngine())

    with app.test_client() as c:
        res = c.get("/data")

    assert res.status_code == 500
    data = res.get_json()
    assert data["error"] == "database query failed"
    assert data.get("detail") == "Boom!"

    app.debug = False
