"""PAIR C. Partner locator, router, and reachability layer."""
from fastapi import APIRouter

from app.schemas import ChannelOut, ReachabilityCell, RouteOut

router = APIRouter(prefix="/api/locator", tags=["locator"])


@router.get("/channels", response_model=list[ChannelOut])
def channels(district_code: str | None = None):
    return []


@router.get("/route", response_model=RouteOut)
def route(from_lat: float, from_lon: float, to_channel_id: str):
    """Mappls Directions. Falls back to a straight line + fixture when OFFLINE_MODE."""
    return RouteOut(distance_km=0, duration_min=0,
                    geometry={"type": "LineString", "coordinates": []},
                    provider="fixture")


@router.get("/reachability", response_model=list[ReachabilityCell])
def reachability():
    """Telangana and Ladakh have no SCA at all. That is the map's argument."""
    return []
