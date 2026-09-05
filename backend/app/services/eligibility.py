"""
PAIR A. Evaluate each atomic condition SEPARATELY and keep the result.

A single nested JSONLogic expression returns a boolean, and a boolean cannot
express provenance or counterfactuals - which is the entire differentiator
against myScheme. So: one Condition per rule, one ConditionResult per Condition.
"""
from dataclasses import dataclass

from app.schemas import ConditionResult, Provenance, Verdict


@dataclass
class Condition:
    id: str
    logic: dict          # {"<=": [{"var": "family_income"}, 500000]}
    human_text: str
    provenance: list[Provenance]


def evaluate(conditions: list[Condition], profile: dict) -> tuple[Verdict, list[ConditionResult]]:
    from json_logic import jsonLogic   # verify import path against installed package

    results, any_missing, any_conflict = [], False, False

    for c in conditions:
        if not c.provenance:
            any_missing = True
            results.append(ConditionResult(
                condition_id=c.id, passed=None, human_text=c.human_text,
                counterfactual="Not published on any official page we could fetch.",
            ))
            continue

        # More than one live provenance with different thresholds => the
        # government disagrees with itself. Surface both, never pick one.
        distinct = {p.source_url for p in c.provenance}
        outcome = bool(jsonLogic(c.logic, profile))
        if len(distinct) > 1 and _sources_disagree(c):
            any_conflict = True

        results.append(ConditionResult(
            condition_id=c.id, passed=outcome, human_text=c.human_text,
            provenance=c.provenance,
        ))

    if any_conflict:
        return Verdict.CONTRADICTORY_SOURCES, results
    if any_missing:
        return Verdict.INSUFFICIENT_DATA, results
    if all(r.passed for r in results):
        return Verdict.ELIGIBLE, results
    return Verdict.NOT_ELIGIBLE, results


def _sources_disagree(c: Condition) -> bool:
    """TODO Pair A: compare threshold values across live rule_version rows."""
    return False
