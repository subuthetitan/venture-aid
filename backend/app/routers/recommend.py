"""PAIR A. Owns this file. Nobody else edits it."""
import json
from pathlib import Path

from fastapi import APIRouter

from app.schemas import ApplicantProfile, RecommendResponse

router = APIRouter(prefix="/api/recommend", tags=["recommend"])
FIXTURE = Path(__file__).parent.parent / "fixtures" / "recommend.json"


@router.post("", response_model=RecommendResponse)
def recommend(profile: ApplicantProfile) -> RecommendResponse:
    # DAY ZERO: returns a fixture so the frontend is never blocked.
    # Replace the body with the real eligibility call; keep the response shape.
    data = json.loads(FIXTURE.read_text())
    return RecommendResponse(**data)
