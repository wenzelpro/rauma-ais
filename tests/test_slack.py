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
    assert "Test" in messages[0]
