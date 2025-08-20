import json
import os
import threading
import time
from typing import Dict, List, Optional, Set

import requests
from flask import Flask, render_template
from shapely.geometry import shape

TOKEN_URL = "https://id.barentswatch.no/connect/token"
AIS_URL = "https://historical.ais.barentswatch.no/api/v2/TrafficDataByPolygon"
SCOPE = "aisapi"


def load_polygon(path: str) -> str:
    """Load polygon from a GeoJSON file and return it as WKT string."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    geom = shape(data["features"][0]["geometry"])
    return geom.wkt


def get_token(client_id: str, client_secret: str) -> str:
    """Obtain OAuth token from BarentsWatch."""
    data = {"grant_type": "client_credentials", "scope": SCOPE}
    resp = requests.post(
        TOKEN_URL, data=data, auth=(client_id, client_secret), timeout=30
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


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
    client_id = os.environ.get("BW_CLIENT_ID")
    client_secret = os.environ.get("BW_CLIENT_SECRET")

    current_vessels: List[Dict] = []
    seen: Set[str] = set()
    token: Optional[str] = None

    def update_vessels() -> None:
        """Background thread that refreshes vessel list every 10 minutes."""
        nonlocal token
        if not client_id or not client_secret:
            print("BW_CLIENT_ID and BW_CLIENT_SECRET must be set")
            return
        token = get_token(client_id, client_secret)
        while True:
            try:
                vessels = fetch_vessels(token, polygon_wkt)
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 401:
                    token = get_token(client_id, client_secret)
                    vessels = fetch_vessels(token, polygon_wkt)
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

    @app.before_first_request
    def start_update_thread() -> None:
        threading.Thread(target=update_vessels, daemon=True).start()

    @app.route("/")
    def index() -> str:
        return render_template("index.html", vessels=current_vessels)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

