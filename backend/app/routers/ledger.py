"""PAIR C. Transparency Ledger. Synthetic data, labelled as such."""
from fastapi import APIRouter

from app.schemas import LedgerResponse

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


@router.get("", response_model=LedgerResponse)
def ledger():
    return LedgerResponse(cells=[])
