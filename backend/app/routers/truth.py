"""PAIR A. Scheme Truth Layer - registry + live contradictions."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/truth", tags=["truth"])


@router.get("/contradictions")
def contradictions():
    """Backed by the live_contradiction SQL view once rule_version is seeded."""
    return [{
        "scheme_id": "nsfdc.suvidha",
        "field": "family_income_ceiling",
        "positions": [
            {"value": {"amount": 500000}, "source": "https://nsfdc.nic.in/about-us-3",
             "authority": "NSFDC", "observed_at": "2026-09-03"},
            {"value": {"amount": 300000}, "source": "https://nsfdc.nic.in/en/how-to-apply",
             "authority": "NSFDC", "observed_at": "2026-09-03"},
            {"value": {"amount": 300000}, "source": "https://socialjustice.gov.in/schemes/34",
             "authority": "MoSJE", "observed_at": "2026-09-03"},
        ],
    }]
