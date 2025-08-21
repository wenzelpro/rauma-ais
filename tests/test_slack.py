import app

def test_notify_new_ship(monkeypatch):
    messages = []

    def fake_post(url, json, timeout):
        messages.append(json["text"])
        class Resp:
            status_code = 200
        return Resp()

    monkeypatch.setattr(app, "SLACK_WEBHOOK_URL", "http://example.com")
    monkeypatch.setattr(app.requests, "post", fake_post)
    app._known_mmsi.clear()
    if app._engine and app._seen_table is not None:
        with app._engine.begin() as conn:
            conn.execute(app._seen_table.delete())


    ship = {"mmsi": 123, "name": "Test", "latitude": 1, "longitude": 2}
    app.notify_new_ships([ship])
    app.notify_new_ships([ship])

    assert len(messages) == 1
    msg = messages[0]    assert msg.startswith(
        "Unknown: Test seiler mot Unknown. Lengde: Unknown. Flagg:"
    )

    assert "Name: Test" in msg
    assert "Destination: Unknown" in msg
    assert "Length: Unknown" in msg
    assert "Type: Unknown" in msg
    assert "Norway" in msg

def test_persistence_across_runs(monkeypatch, tmp_path):
    messages = []

    def fake_post(url, json, timeout):
        messages.append(json["text"])
        class Resp:
            status_code = 200
        return Resp()

    db_url = f"sqlite:///{tmp_path}/seen.db"
    monkeypatch.setattr(app, "DATABASE_URL", db_url)
    monkeypatch.setattr(app, "SLACK_WEBHOOK_URL", "http://example.com")
    monkeypatch.setattr(app.requests, "post", fake_post)

    # Reset app DB state
    app._known_mmsi.clear()
    app._engine = None
    app._seen_table = None
    app._init_db()

    ship = {"mmsi": "999", "name": "Persist", "latitude": 1, "longitude": 2}
    app.notify_new_ships([ship])

    # Simulate new process by clearing in-memory set and reloading from DB
    app._known_mmsi.clear()
    app._init_db()
    app.notify_new_ships([ship])

    assert len(messages) == 1
