import app
from sqlalchemy import text, select


def test_data_recreates_missing_table(monkeypatch, tmp_path):
    db_url = f"sqlite:///{tmp_path}/seen.db"
    monkeypatch.setattr(app, "DATABASE_URL", db_url)

    # Reset state and create initial table
    app._known_mmsi.clear()
    app._engine = None
    app._seen_table = None
    app._init_db()

    # Drop the table to simulate a missing table scenario
    with app._engine.begin() as conn:
        conn.execute(text("DROP TABLE seen_mmsi"))

    client = app.app.test_client()
    resp = client.get("/data")

    assert resp.status_code == 200
    assert resp.get_json() == {"rows": []}

    # Ensure the table was recreated
    with app._engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='seen_mmsi'"))
        assert rows.fetchone() is not None


def test_clear_endpoint(monkeypatch, tmp_path):
    db_url = f"sqlite:///{tmp_path}/seen.db"
    monkeypatch.setattr(app, "DATABASE_URL", db_url)

    # Reset app state and initialize DB
    app._known_mmsi.clear()
    app._engine = None
    app._seen_table = None
    app._init_db()

    ship = {"mmsi": 123, "name": "X", "latitude": 1, "longitude": 2}
    app.notify_new_ships([ship])

    client = app.app.test_client()
    resp = client.delete("/data")

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "cleared"}
    assert app._known_mmsi == set()
    with app._engine.connect() as conn:
        rows = conn.execute(select(app._seen_table)).fetchall()
        assert rows == []
