from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone

from app import _load_default_geometry, _validate_area, bw_client, notify_new_ships

logging.basicConfig(level="INFO")
logger = logging.getLogger("poller")


def main() -> None:
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
        logger.info("Fetched %d ships", len(features))
    except Exception as exc:
        logger.exception("Poller failed: %s", exc)


if __name__ == "__main__":
    main()
