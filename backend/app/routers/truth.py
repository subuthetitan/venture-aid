"""PAIR A. Scheme Truth Layer - registry + live contradictions."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RuleVersion, Scheme
from app.services.eligibility import hashable_value

router = APIRouter(prefix="/api/truth", tags=["truth"])


@router.get("/contradictions")
def contradictions(db: Session = Depends(get_db)):
    """
    Backed by rule_version now that it's seeded (see services/seed_truth_layer.py).
    Groups live (non-superseded) rows by (scheme_id, field) and returns any
    group where the values actually differ - the live_contradiction view
    from the MVP plan, expressed here as a Python group-by since we're
    already holding a Session rather than raw SQL.
    """
    rows = db.execute(
        select(RuleVersion, Scheme.name)
        .join(Scheme, Scheme.id == RuleVersion.scheme_id)
        .where(RuleVersion.superseded_at.is_(None))
    ).all()

    groups: dict[tuple[str, str], list] = {}
    scheme_names: dict[str, str] = {}
    for rv, scheme_name in rows:
        key = (rv.scheme_id, rv.field)
        groups.setdefault(key, []).append(rv)
        scheme_names[rv.scheme_id] = scheme_name

    out = []
    for (scheme_id, field_name), versions in groups.items():
        distinct_values = {hashable_value(v.value) for v in versions}
        if len(distinct_values) <= 1:
            continue
        out.append({
            "scheme_id": scheme_id,
            "scheme_name": scheme_names[scheme_id],
            "field": field_name,
            "positions": [
                {
                    "value": v.value,
                    "source": v.source_url,
                    "authority": v.source_authority,
                    "observed_at": v.observed_at.date().isoformat(),
                    **({"effective_from": v.effective_from.isoformat()} if v.effective_from else {}),
                }
                for v in versions
            ],
        })
    return out
