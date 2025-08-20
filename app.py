import json
import os
import threading
import time
from typing import Dict, List, Set

import requests
from flask import Flask, render_template
from shapely.geometry import shape

AIS_URL = "https://historical.ais.barentswatch.no/api/v2/TrafficDataByPolygon"


def load_polygon(path: str) -> str:
    """Load polygon from a GeoJSON file and return it as WKT string."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    geom = shape(data["features"][0]["geometry"])
    return geom.wkt

def fetch_vessels(token: str, polygon_wkt: str) -> List[Dict]:
    """Fetch vessel traffic within the polygon."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"polygon": polygon_wkt}
    resp = requests.get(AIS_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def create_app() -> Flask:
    """Create Flask application with background vessel updater."""

    app = Flask(__name__)

    polygon_wkt = load_polygon("map.geojson")
    token = os.environ.get("BW_ACCESS_TOKEN")

    current_vessels: List[Dict] = []
    seen: Set[str] = set()

    def update_vessels() -> None:
        """Background thread that refreshes vessel list every 10 minutes."""
        if not token:
            print("BW_ACCESS_TOKEN must be set")
            return
        while True:
            try:
                vessels = fetch_vessels(token, polygon_wkt)
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 401:
                    print("Access token expired or invalid; update BW_ACCESS_TOKEN")
                else:
                    print(f"Error fetching vessels: {exc}")
                time.sleep(600)
                continue

            for vessel in vessels:
                mmsi = str(vessel.get("mmsi"))
                if mmsi not in seen:
                    name = vessel.get("name", "Unknown")
                    print(f"New vessel: {mmsi}: {name}")
                    seen.add(mmsi)

            current_vessels.clear()
            current_vessels.extend(vessels)
            time.sleep(600)

    threading.Thread(target=update_vessels, daemon=True).start()

    @app.route("/")
    def index() -> str:
        return render_template("index.html", vessels=current_vessels)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

