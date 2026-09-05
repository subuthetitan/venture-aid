"""PAIR B. Fully real from day one - no fixture needed."""
from fastapi import APIRouter

from app.schemas import CalculateRequest, CalculateResponse
from app.services import finance

router = APIRouter(prefix="/api/calculate", tags=["calculate"])


@router.post("", response_model=CalculateResponse)
def calculate(req: CalculateRequest) -> CalculateResponse:
    return finance.calculate(**req.model_dump())
