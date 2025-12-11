import app


def test_ignore_ship_by_name_and_mmsi(monkeypatch):
    messages: list[str] = []

    def fake_post(url, json, timeout):
        messages.append(json["text"])

        class Resp:
            status_code = 200

        return Resp()

    monkeypatch.setattr(app, "SLACK_WEBHOOK_URL", "http://example.com")
    monkeypatch.setattr(app.requests, "post", fake_post)

    # Reset state and configure ignored ship list
    app._known_mmsi.clear()
    app._ignored_ships = [{"name": "Amanda", "mmsi": "259032810"}]

    ship = {"mmsi": "259032810", "name": "Amanda", "latitude": 1, "longitude": 2}

    app.notify_new_ships([ship])

    assert messages == []
    assert 259032810 in app._known_mmsi
