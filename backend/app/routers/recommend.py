"""PAIR A. Owns this file. Nobody else edits it."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RuleVersion, Scheme
from app.schemas import (ApplicantProfile, Provenance, RecommendResponse,
                          SchemeMatch, Verdict)
from app.services.eligibility import Condition, ConditionSource, evaluate
from app.services.seed_truth_layer import load_seed_data

router = APIRouter(prefix="/api/recommend", tags=["recommend"])

# Static loan terms (max_loan, rate) live in the frozen seed file, not the DB -
# they're scheme metadata, not eligibility rules Pair A's Truth Layer tracks
# for contradiction. Cached at import time; it's a handful of rows.
_SEED = load_seed_data()
_SCHEME_TERMS = {s["id"]: s for s in _SEED["schemes"]}


def _conditions_for_scheme(db: Session, scheme_id: str) -> list[Condition]:
    """
    Groups this scheme's rule_version rows by field, dropping any row that's
    been superseded. Two-or-more distinct values surviving in the same group
    is exactly what makes evaluate() return CONTRADICTORY_SOURCES - no
    special-casing needed here.
    """
    rows = db.execute(
        select(RuleVersion)
        .where(RuleVersion.scheme_id == scheme_id, RuleVersion.superseded_at.is_(None))
    ).scalars().all()

    by_field: dict[str, list[RuleVersion]] = {}
    for r in rows:
        by_field.setdefault(r.field, []).append(r)

    field_specs = {
        "family_income_ceiling": ("numeric_max", "family_income",
                                  "Annual family income must not exceed the scheme ceiling"),
        "caste_category": ("category_in", "caste_category",
                           "Applicant must belong to a Scheduled Caste"),
        "age_criteria": ("numeric_max", "age", "Age criteria"),
    }

    conditions = []
    for field_name, (kind, var_name, human_text) in field_specs.items():
        sources = [
            ConditionSource(
                value=r.value,
                provenance=Provenance(
                    source_url=r.source_url,
                    source_authority=r.source_authority,
                    observed_at=r.observed_at.isoformat(),
                    effective_from=r.effective_from.isoformat() if r.effective_from else None,
                ),
            )
            for r in by_field.get(field_name, [])
        ]
        conditions.append(Condition(id=field_name, kind=kind, var_name=var_name,
                                     human_text=human_text, sources=sources))
    return conditions


def _retired_scheme_match(scheme: Scheme) -> SchemeMatch:
    """
    Retired schemes still turn up in search results years later (pain point
    P5 from the discovery report) - show that explicitly instead of quietly
    filtering them out.
    """
    from app.schemas import ConditionResult
    retired_on = _SCHEME_TERMS.get(scheme.id, {}).get("retired_on", "an earlier date")
    return SchemeMatch(
        scheme_id=scheme.id,
        scheme_name=scheme.name,
        verdict=Verdict.NOT_ELIGIBLE,
        conditions=[ConditionResult(
            condition_id="scheme_status",
            passed=False,
            human_text=f"This scheme was retired on {retired_on}. It still ranks in search "
                       f"results but is not currently disbursing loans.",
        )],
    )


@router.post("", response_model=RecommendResponse)
def recommend(profile: ApplicantProfile, db: Session = Depends(get_db)) -> RecommendResponse:
    profile_dict = profile.model_dump()
    schemes = db.execute(select(Scheme)).scalars().all()

    matches = []
    for scheme in schemes:
        if scheme.status == "retired":
            matches.append(_retired_scheme_match(scheme))
            continue

        conditions = _conditions_for_scheme(db, scheme.id)
        verdict, results = evaluate(conditions, profile_dict)

        terms = _SCHEME_TERMS.get(scheme.id, {})
        disagreement_note = None
        if verdict == Verdict.CONTRADICTORY_SOURCES:
            disagreement_note = (
                "Two Government of India pages publish different figures for this scheme. "
                f"At your stated income of Rs {profile.family_income:,} one source says you "
                "qualify and another says you do not. Both links are shown below, with the "
                "dates we checked them."
            )

        matches.append(SchemeMatch(
            scheme_id=scheme.id,
            scheme_name=scheme.name,
            verdict=verdict,
            conditions=results,
            max_loan=terms.get("max_loan"),
            interest_rate=terms.get("rate_to_beneficiary"),
            disagreement_note=disagreement_note,
        ))

    # rank: confirmed eligible first, then the reveal, then the rest
    rank = {Verdict.ELIGIBLE: 0, Verdict.CONTRADICTORY_SOURCES: 1,
            Verdict.INSUFFICIENT_DATA: 2, Verdict.NOT_ELIGIBLE: 3}
    matches.sort(key=lambda m: rank[m.verdict])

    return RecommendResponse(matches=matches, seeded=True)
