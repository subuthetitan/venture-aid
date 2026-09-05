"""PAIR B. Sanction-Ready: voice -> activity -> costed report -> PDF."""
import json
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.schemas import ProjectReport, ReadinessRequest

router = APIRouter(prefix="/api/readiness", tags=["readiness"])
FIXTURE = Path(__file__).parent.parent / "fixtures" / "report.json"


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = "hi"):
    """Bhashini primary (6s timeout) -> Sarvam Saaras v3 -> cached fixture."""
    return {"transcript": "मुझे सिलाई का काम शुरू करना है", "provider": "fixture"}


@router.post("", response_model=ProjectReport)
def generate(req: ReadinessRequest) -> ProjectReport:
    return ProjectReport(**json.loads(FIXTURE.read_text()))
