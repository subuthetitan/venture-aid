"""PAIR B. Fully real from day one - no fixture needed."""
from fastapi import APIRouter, HTTPException

from app.schemas import CalculateRequest, CalculateResponse
from app.services import finance

router = APIRouter(prefix="/api/calculate", tags=["calculate"])


@router.get("/schemes")
def schemes() -> list[dict]:
    """The schemes this calculator can model, with their terms.

    Exists so the frontend does not have to hardcode SCHEME_TERMS. That
    duplicated list was already flagged in Calculator.jsx as able to drift out
    of sync with the backend; serving it removes the whole failure mode.

    `women_only` mirrors WOMEN_ONLY_SCHEMES in routers/readiness.py. It is
    advisory here -- this endpoint collects no applicant gender and makes no
    eligibility determination -- but a caller must be able to see that the
    restriction exists before quoting an EMI.
    """
    from app.routers.readiness import WOMEN_ONLY_SCHEMES

    return [
        {
            "scheme_id": scheme_id,
            "interest_rate": terms["rate"],
            "tenure_months": terms["tenure"],
            "moratorium_months": terms["moratorium"],
            "max_loan": terms["max_loan"],
            "women_only": scheme_id in WOMEN_ONLY_SCHEMES,
        }
        for scheme_id, terms in finance.SCHEME_TERMS.items()
    ]


@router.post("", response_model=CalculateResponse)
def calculate(req: CalculateRequest) -> CalculateResponse:
    try:
        return finance.calculate(**req.model_dump())
    except finance.UnknownScheme:
        # Previously a bare KeyError escaping as a 500. Same shape as the
        # readiness errors, so the frontend can render a recovery path.
        raise HTTPException(
            status_code=422,
            detail={
                "error": "UNKNOWN_SCHEME",
                "message": (
                    f"No published terms for scheme_id '{req.scheme_id}'. We only "
                    "model schemes whose rate, tenure and ceiling are published."
                ),
                "supported_schemes": sorted(finance.SCHEME_TERMS),
            },
        ) from None
