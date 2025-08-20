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

# ---------------------------------------------------------------------------
# Slack notifications
# ---------------------------------------------------------------------------

# Simple in-process rate limiting
last_notify_epoch = 0


@app.post("/notify")
def notify_slack():
    import time
    import requests

    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        return jsonify({"error": "Slack not configured"}), 501

    global last_notify_epoch
    now = time.time()
    if now - last_notify_epoch < 60:
        return jsonify({"error": "Rate limited"}), 429

    payload = request.get_json(force=True) or {}
    ships = payload.get("ships", [])
    if not ships:
        return jsonify({"ok": True, "notified": 0})

    lines = []
    for s in ships:
        name = s.get("name") or "Ukjent"
        lines.append(
            f"• {name} (MMSI {s.get('mmsi')}) – {s.get('latitude')},{s.get('longitude')} – {s.get('msgtime')}"
        )

    text = f"*Nye skip innenfor området ({len(ships)})*\n" + "\n".join(lines)
    resp = requests.post(webhook, json={"text": text}, timeout=10)
    if resp.status_code >= 300:
        return jsonify({"error": f"Slack error {resp.status_code}", "body": resp.text}), 502

    last_notify_epoch = now
    return jsonify({"ok": True, "notified": len(ships)})


@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp

if __name__ == "__main__":
    # For local dev only. In Heroku, gunicorn (Procfile) will run the app.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
