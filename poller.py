from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

import app
from app import _load_default_geometry, _validate_area, bw_client, notify_new_ships

import argparse

logging.basicConfig(level="INFO")
logger = logging.getLogger("poller")


def cleanup_seen_mmsi(max_age_hours: int = 24) -> None:
    if not app._engine or app._seen_table is None:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    try:
        with app._engine.begin() as conn:
            conn.execute(
                app._seen_table.delete().where(app._seen_table.c.last_seen < cutoff)
            )
    except SQLAlchemyError as exc:
        logger.warning("Cleanup failed: %s", exc)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the seen_mmsi database and exit",
    )
    args = parser.parse_args(argv)
    if args.clear:
        app.clear_seen_mmsi()
        logger.info("Cleared seen_mmsi database")
        return

    try:
        geom = _load_default_geometry()
        _validate_area(geom)
        now = datetime.now(timezone.utc)
        msgtimefrom = now - timedelta(hours=1)
        mmsi_list = bw_client.find_mmsi_in_area(
            polygon_geometry=geom,
            msgtimefrom=msgtimefrom,
            msgtimeto=now,
        )
        features = bw_client.fetch_latest_combined(mmsi_list)
        notify_new_ships(features)
        cleanup_seen_mmsi()
        logger.info("Fetched %d ships", len(features))
    except Exception as exc:
        logger.exception("Poller failed: %s", exc)


if __name__ == "__main__":
    main()
