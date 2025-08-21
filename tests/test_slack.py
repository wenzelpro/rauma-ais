import app
import poller
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

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


    ship = {"mmsi": 257000000, "name": "Test", "latitude": 1, "longitude": 2}
    app.notify_new_ships([ship])
    app.notify_new_ships([ship])

    assert len(messages) == 1
    msg = messages[0]
    assert msg.startswith("New ship in area:")

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


def test_last_seen_and_cleanup(monkeypatch, tmp_path):
    db_url = f"sqlite:///{tmp_path}/seen.db"
    monkeypatch.setattr(app, "DATABASE_URL", db_url)
    monkeypatch.setattr(app, "SLACK_WEBHOOK_URL", "http://example.com")

    # Reset app DB state
    app._known_mmsi.clear()
    app._engine = None
    app._seen_table = None
    app._init_db()

    class FakeResp:
        status_code = 200

    def fake_post(url, json, timeout):
        return FakeResp()

    monkeypatch.setattr(app.requests, "post", fake_post)

    ship = {"mmsi": 555, "name": "Time", "latitude": 1, "longitude": 2}

    t1 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2020, 1, 2, tzinfo=timezone.utc)

    class FakeDT1:
        @classmethod
        def now(cls, tz=None):
            return t1

    class FakeDT2:
        @classmethod
        def now(cls, tz=None):
            return t2

    monkeypatch.setattr(app, "datetime", FakeDT1)
    app.notify_new_ships([ship])
    with app._engine.begin() as conn:
        first_seen = conn.execute(
            select(app._seen_table.c.last_seen)
        ).fetchone()[0]
    assert first_seen == t1.replace(tzinfo=None)

    monkeypatch.setattr(app, "datetime", FakeDT2)
    app.notify_new_ships([ship])
    with app._engine.begin() as conn:
        second_seen = conn.execute(
            select(app._seen_table.c.last_seen)
        ).fetchone()[0]
    assert second_seen == t2.replace(tzinfo=None)

    old_time = t2 - timedelta(hours=48)
    with app._engine.begin() as conn:
        conn.execute(
            app._seen_table.insert().values(mmsi=999, last_seen=old_time)
        )
    monkeypatch.setattr(poller, "datetime", FakeDT2)
    poller.cleanup_seen_mmsi(max_age_hours=24)
    with app._engine.begin() as conn:
        rows = conn.execute(select(app._seen_table.c.mmsi)).fetchall()
        mmsis = {r[0] for r in rows}
    assert 555 in mmsis and 999 not in mmsis
