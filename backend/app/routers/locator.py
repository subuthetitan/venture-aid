"""PAIR C. Partner locator, router, and reachability layer."""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Channel
from app.schemas import ChannelOut, ReachabilityCell, RouteOut
from app.services.routing import get_route

router = APIRouter(prefix="/api/locator", tags=["locator"])

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@lru_cache(maxsize=1)
def _districts() -> dict:
    return json.loads((FIXTURES / "district_codes.json").read_text(encoding="utf-8"))


@router.get("/channels", response_model=list[ChannelOut])
def channels(district_code: str | None = None, db: Session = Depends(get_db)):
    """Channels in a district. Omit district_code to list everything seeded."""
    q = db.query(Channel)
    if district_code:
        q = q.filter(Channel.district_code == district_code)
    return q.order_by(Channel.kind, Channel.name).all()


@router.get("/route", response_model=RouteOut)
async def route(from_lat: float, from_lon: float, to_channel_id: str,
                db: Session = Depends(get_db)):
    """Mappls Directions. Falls back to a straight line when OFFLINE_MODE."""
    channel = db.query(Channel).filter(Channel.id == to_channel_id).first()
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.lat is None or channel.lon is None:
        raise HTTPException(status_code=422, detail="Channel has no verified coordinates")

    return await get_route(from_lat, from_lon, float(channel.lat), float(channel.lon))


@router.get("/reachability", response_model=list[ReachabilityCell])
def reachability(db: Session = Depends(get_db)):
    """
    Telangana and Ladakh have no SCA at all. That is the map's argument.

    Derived, not stored: channel counts come from the channel table, has_sca from
    the district fixture. No extra table means no extra migration mid-build.

    Three states, not two. has_sca false means we have positive evidence there is
    no channel. has_sca true with zero channels means we have not checked. Absence
    of data must never render as presence of a channel.
    """
    counts = dict(
        db.query(Channel.district_code, func.count(Channel.id))
        .group_by(Channel.district_code)
        .all()
    )

    data = _districts()
    states = data["states"]
    cells: list[ReachabilityCell] = []

    for d in data["districts"]:
        state = states.get(d["state_code"], {})
        has_sca = bool(state.get("has_sca", False))
        count = counts.get(d["district_code"], 0)

        if not has_sca:
            note = state.get("no_sca_note", "No SCA in this state")
        elif count == 0:
            note = "No channel recorded. We have not verified this district."
        else:
            note = None

        cells.append(ReachabilityCell(
            district_code=d["district_code"],
            state_code=d["state_code"],
            has_sca=has_sca,
            channel_count=count,
            note=note,
        ))
    return cells