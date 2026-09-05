"""
Mappls Directions with a guaranteed fallback.

The only live external call in the MVP, which makes it the only thing that can
fail on stage. Any failure - no key, offline_mode, timeout, bad response -
returns a straight line with provider='fixture'. Dead wifi degrades the route,
never the map.

Auth: Mappls issued this project a Static Key rather than an OAuth client pair,
so the key goes directly in the URL path. No token exchange, nothing to expire.
"""
import math

import httpx

from app.config import settings
from app.schemas import RouteOut

TIMEOUT_S = 6.0
ASSUMED_ROAD_SPEED_KMH = 30.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _fixture_route(f_lat: float, f_lon: float, t_lat: float, t_lon: float) -> RouteOut:
    km = _haversine_km(f_lat, f_lon, t_lat, t_lon)
    return RouteOut(
        distance_km=round(km, 1),
        duration_min=round(km / ASSUMED_ROAD_SPEED_KMH * 60, 0),
        geometry={"type": "LineString", "coordinates": [[f_lon, f_lat], [t_lon, t_lat]]},
        provider="fixture",
    )


async def get_route(f_lat: float, f_lon: float, t_lat: float, t_lon: float) -> RouteOut:
    if settings.offline_mode or not settings.mappls_static_key:
        return _fixture_route(f_lat, f_lon, t_lat, t_lon)

    url = (
        f"https://apis.mappls.com/advancedmaps/v1/{settings.mappls_static_key}"
        f"/route_adv/driving/{f_lon},{f_lat};{t_lon},{t_lat}"
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params={"geometries": "geojson", "overview": "full"},
                timeout=TIMEOUT_S,
            )
            resp.raise_for_status()
            route = resp.json()["routes"][0]
            return RouteOut(
                distance_km=round(route["distance"] / 1000, 1),
                duration_min=round(route["duration"] / 60, 0),
                geometry=route["geometry"],
                provider="mappls",
            )
    except Exception:
        return _fixture_route(f_lat, f_lon, t_lat, t_lon)