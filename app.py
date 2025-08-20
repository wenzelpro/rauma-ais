# app.py
from __future__ import annotations
import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv

from barentswatch import BarentsWatchClient
from geometry_utils import (
    ensure_valid_polygon_geometry,
    geometry_area_km2,
)

# Load environment (local dev)
load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("barentswatch-geoapp")

app = Flask(__name__)

# Configuration
DEFAULT_GEOJSON_PATH = os.getenv("GEOJSON_PATH", "map.geojson")
MAX_AREA_KM2 = float(os.getenv("MAX_AREA_KM2", "500"))

# Initialize BarentsWatch client (token management inside)
bw_client = BarentsWatchClient(
    client_id=os.getenv("BW_CLIENT_ID"),
    client_secret=os.getenv("BW_CLIENT_SECRET"),
    static_access_token=os.getenv("BW_ACCESS_TOKEN"),
    token_url=os.getenv("BW_TOKEN_URL", "https://id.barentswatch.no/connect/token"),
)

def _load_default_geometry() -> Dict[str, Any]:
    """Load geometry from DEFAULT_GEOJSON_PATH (Polygon or MultiPolygon)."""
    if not os.path.exists(DEFAULT_GEOJSON_PATH):
        raise FileNotFoundError(f"GeoJSON file not found: {DEFAULT_GEOJSON_PATH}")
    with open(DEFAULT_GEOJSON_PATH, "r", encoding="utf-8") as f:
        gj = json.load(f)
    # Allow either a FeatureCollection/Feature or direct geometry
    if gj.get("type") == "FeatureCollection":
        if not gj.get("features"):
            raise ValueError("FeatureCollection has no features")
        geom = gj["features"][0].get("geometry")
    elif gj.get("type") == "Feature":
        geom = gj.get("geometry")
    else:
        geom = gj  # assume bare geometry
    geom = ensure_valid_polygon_geometry(geom)
    return geom

def _validate_area(geom: Dict[str, Any]) -> float:
    area_km2 = geometry_area_km2(geom)
    if area_km2 > MAX_AREA_KM2:
        raise ValueError(f"Area too large: {area_km2:.1f} km^2 (max {MAX_AREA_KM2} km^2)")
    return area_km2

@app.get("/")
def index():
    return render_template("index.html",
                           max_area_km2=MAX_AREA_KM2,
                           default_geojson_path=DEFAULT_GEOJSON_PATH)

@app.get("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})

@app.get("/ships")
def get_ships():
    try:
        geom = _load_default_geometry()
        area_km2 = _validate_area(geom)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    now = datetime.now(timezone.utc)
    # Siste 1 time
    msgtimefrom = now - timedelta(hours=1)

    try:
        mmsi_list = bw_client.find_mmsi_in_area(
            polygon_geometry=geom,
            msgtimefrom=msgtimefrom,
            msgtimeto=now,
        )
        features = bw_client.fetch_latest_combined(mmsi_list)
    except Exception as e:
        logger.exception("BarentsWatch error")
        return jsonify({"error": f"Upstream error: {e}"}), 502

    return jsonify({"count": len(features), "features": features, "area_km2": round(area_km2, 3)})

@app.post("/ships")
def post_ships():
    try:
        payload = request.get_json(force=True, silent=False)
        if not payload:
            return jsonify({"error": "Expected JSON body"}), 400
        # Either full GeoJSON feature/collection or direct 'geometry'
        geom = payload.get("geometry", payload)
        geom = ensure_valid_polygon_geometry(geom)
        area_km2 = _validate_area(geom)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    now = datetime.now(timezone.utc)
    # Siste 1 time
    msgtimefrom = now - timedelta(hours=1)

    try:
        mmsi_list = bw_client.find_mmsi_in_area(
            polygon_geometry=geom,
            msgtimefrom=msgtimefrom,
            msgtimeto=now,
        )
        features = bw_client.fetch_latest_combined(mmsi_list)
    except Exception as e:
        logger.exception("BarentsWatch error")
        return jsonify({"error": f"Upstream error: {e}"}), 502

    return jsonify({"count": len(features), "features": features, "area_km2": round(area_km2, 3)})

if __name__ == "__main__":
    # For local dev only. In Heroku, gunicorn (Procfile) will run the app.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
