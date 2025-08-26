# barentswatch.py
from __future__ import annotations
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import requests

DEFAULT_FIND_IN_AREA_URL = "https://historic.ais.barentswatch.no/v1/historic/mmsiinarea"
DEFAULT_LATEST_COMBINED_URL = "https://live.ais.barentswatch.no/v1/latest/combined"

class BarentsWatchClient:
    def __init__(
        self,
        client_id: Optional[str],
        client_secret: Optional[str],
        static_access_token: Optional[str] = None,
        token_url: str = "https://id.barentswatch.no/connect/token",
        find_in_area_url: str = DEFAULT_FIND_IN_AREA_URL,
        latest_combined_url: str = DEFAULT_LATEST_COMBINED_URL,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.static_access_token = static_access_token
        self.token_url = token_url
        self.find_in_area_url = find_in_area_url
        self.latest_combined_url = latest_combined_url
        self._session = session or requests.Session()
        self._token: Optional[str] = None
        self._token_expiry_epoch: float = 0.0

    # -------------------------
    # OAuth2 Client Credentials
    # -------------------------
    def _get_access_token(self) -> str:
        # If a static token is provided and no client creds, use it as-is
        if self.static_access_token and not (self.client_id and self.client_secret):
            return self.static_access_token

        # Cached?
        now = time.time()
        if self._token and now < self._token_expiry_epoch - 30:
            return self._token

        if not (self.client_id and self.client_secret):
            raise RuntimeError("Missing BW_CLIENT_ID / BW_CLIENT_SECRET (or BW_ACCESS_TOKEN)")

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "ais",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = self._session.post(self.token_url, data=data, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Token request failed: {resp.status_code} {resp.text}")
        token_payload = resp.json()
        self._token = token_payload["access_token"]
        # Compute expiry
        expires_in = int(token_payload.get("expires_in", 3600))
        self._token_expiry_epoch = now + expires_in
        return self._token

    # ------------------------------------
    # Historic: find MMSI within a polygon
    # ------------------------------------
    def find_mmsi_in_area(
        self,
        polygon_geometry: Dict[str, Any],
        msgtimefrom: datetime,
        msgtimeto: datetime,
    ) -> List[int]:
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "msgtimefrom": msgtimefrom.replace(microsecond=0, tzinfo=timezone.utc).isoformat(),
            "msgtimeto": msgtimeto.replace(microsecond=0, tzinfo=timezone.utc).isoformat(),
            "polygon": polygon_geometry,
        }
        resp = self._session.post(self.find_in_area_url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"find_mmsi_in_area failed: {resp.status_code} {resp.text}")
        data = resp.json()
        # data is expected to be a list of MMSI ints (or objects with mmsi?)
        if isinstance(data, list):
            # Normalize list of ints or dicts
            mmsi = []
            for item in data:
                if isinstance(item, int):
                    mmsi.append(item)
                elif isinstance(item, dict) and "mmsi" in item:
                    mmsi.append(int(item["mmsi"]))
            return mmsi
        raise RuntimeError("Unexpected response for mmsiinarea")

    # --------------------------------------------
    # Live: fetch latest combined positions by MMSI
    # --------------------------------------------
    def fetch_latest_combined(self, mmsi_list: List[int], batch_size: int = 300) -> List[Dict[str, Any]]:
        if not mmsi_list:
            return []
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        results: List[Dict[str, Any]] = []
        for i in range(0, len(mmsi_list), batch_size):
            chunk = mmsi_list[i:i+batch_size]
            payload = {"mmsi": chunk}
            resp = self._session.post(self.latest_combined_url, headers=headers, json=payload, timeout=60)
            if resp.status_code != 200:
                raise RuntimeError(f"latest/combined failed: {resp.status_code} {resp.text}")
            data = resp.json()
            # Normalize to a simple list of features
            for item in data if isinstance(data, list) else []:
                length = (
                    item.get("length")
                    or item.get("lengthoverall")
                    or item.get("lengthOverall")
                )
                simplified = {
                    "mmsi": item.get("mmsi"),
                    "name": item.get("name"),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "msgtime": item.get("msgtime"),
                    "shipType": item.get("shipType"),
                    "destination": item.get("destination"),
                    "length": length,
                }
                results.append(simplified)
        return results
