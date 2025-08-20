# geometry_utils.py
from __future__ import annotations
from typing import Dict, Any

from shapely.geometry import shape
from shapely.ops import transform
from pyproj import CRS, Transformer

def ensure_valid_polygon_geometry(geom: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(geom, dict) or "type" not in geom:
        raise ValueError("Invalid geometry: expected GeoJSON geometry object")
    if geom["type"] not in ("Polygon", "MultiPolygon"):
        raise ValueError(f"Unsupported geometry type: {geom['type']}. Use Polygon or MultiPolygon.")
    # Quick shapely validation
    _ = shape(geom)
    return geom

def _utm_crs_for_lonlat(lon: float, lat: float) -> CRS:
    zone = int((lon + 180) // 6) + 1
    # North if lat >= 0 else South
    if lat >= 0:
        return CRS.from_epsg(32600 + zone)  # WGS84 / UTM zone N
    else:
        return CRS.from_epsg(32700 + zone)  # WGS84 / UTM zone S

def geometry_area_km2(geom: Dict[str, Any]) -> float:
    """Compute area in square kilometers using an appropriate UTM projection."""
    shp = shape(geom)
    centroid = shp.centroid
    lon, lat = centroid.x, centroid.y
    src = CRS.from_epsg(4326)
    dst = _utm_crs_for_lonlat(lon, lat)
    transformer = Transformer.from_crs(src, dst, always_xy=True)
    proj = lambda x, y: transformer.transform(x, y)
    shp_m = transform(proj, shp)  # meters
    area_m2 = shp_m.area
    return area_m2 / 1_000_000.0
