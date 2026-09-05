"""PAIR C. Transparency Ledger. Synthetic data, labelled as such."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import LedgerCell, LedgerResponse

router = APIRouter(prefix="/api/ledger", tags=["ledger"])

# Districts with fewer than this many records are suppressed entirely.
K_ANONYMITY_THRESHOLD = 5

AGG_SQL = text("""
WITH applied AS (
    SELECT application_ref, district_code, MIN(occurred_on) AS applied_on
    FROM application_milestone
    WHERE stage = 'APPLIED'
    GROUP BY application_ref, district_code
),
sanctioned AS (
    SELECT application_ref, MIN(occurred_on) AS sanctioned_on
    FROM application_milestone
    WHERE stage = 'SANCTIONED'
    GROUP BY application_ref
)
SELECT
    a.district_code,
    COUNT(*) AS applications,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY (s.sanctioned_on - a.applied_on)
    ) AS median_days
FROM applied a
LEFT JOIN sanctioned s ON s.application_ref = a.application_ref
GROUP BY a.district_code
ORDER BY a.district_code
""")


@router.get("", response_model=LedgerResponse)
def ledger(db: Session = Depends(get_db)):
    """
    District-level pendency, aggregated from self-reported milestones.

    k-anonymity is implemented, not merely asserted: any district with fewer
    than five applications is suppressed entirely rather than shown with a
    small-n figure.

    No rejection rate is exposed. The generator produces REJECTED milestones so
    the state machine has terminal states, but no Indian government credit
    scheme publishes a rejection figure, so there is no ground truth to
    validate one against. Showing a number here would invent a statistic.
    """
    cells: list[LedgerCell] = []
    for row in db.execute(AGG_SQL):
        suppressed = row.applications < K_ANONYMITY_THRESHOLD
        cells.append(LedgerCell(
            district_code=row.district_code,
            applications=0 if suppressed else row.applications,
            median_days_to_sanction=(
                None if suppressed or row.median_days is None
                else int(round(float(row.median_days)))
            ),
            suppressed=suppressed,
        ))
    return LedgerResponse(cells=cells)