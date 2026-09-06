"""
PAIR A. Evaluate each atomic condition SEPARATELY and keep the result.

A single nested JSONLogic expression returns a boolean, and a boolean cannot
express provenance or counterfactuals - which is the entire differentiator
against myScheme. So: one Condition per rule, one ConditionResult per Condition.

A Condition can be backed by MORE THAN ONE source. When those sources
publish different values for the same field, that's not an error to
resolve - it's the CONTRADICTORY_SOURCES verdict, and both values must
survive into the response so a judge can open both links.

`kind` tells this module how to turn a raw source value into a JSON-Logic
rule and into human-readable actual/threshold text, without hardcoding
per-field logic here. Two kinds cover everything Pair A's seed data needs:
  - "numeric_max": value = {"amount": <number>}      e.g. income ceilings
  - "category_in": value = {"allowed": [<strings>]}  e.g. caste category
Add a new kind here (and only here) if a future condition needs a new shape.
"""
from dataclasses import dataclass, field
from typing import Any

from json_logic import jsonLogic

from app.schemas import ConditionResult, Provenance, Verdict


@dataclass
class ConditionSource:
    value: Any                 # e.g. {"amount": 300000} or {"allowed": ["SC"]}
    provenance: Provenance


@dataclass
class Condition:
    id: str                        # 'income_ceiling'
    kind: str                      # 'numeric_max' | 'category_in'
    var_name: str                  # profile field this reads, e.g. 'family_income'
    human_text: str
    sources: list[ConditionSource] = field(default_factory=list)


def hashable_value(value: Any):
    """
    Makes dict/list values like {"amount": 300000} or {"allowed": ["SC"]}
    comparable in a set. Used here and by routers/truth.py, which needs the
    same "are these two rule_version rows actually different" check.
    """
    if isinstance(value, dict):
        return tuple(sorted((k, hashable_value(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(hashable_value(v) for v in value)
    return value


_hashable = hashable_value  # short alias used throughout this module


def _rule(kind: str, value: dict) -> dict:
    if kind == "numeric_max":
        return {"<=": [{"var": "x"}, value["amount"]]}
    if kind == "category_in":
        return {"in": [{"var": "x"}, value["allowed"]]}
    raise ValueError(f"unknown condition kind: {kind}")


def _apply(kind: str, value: dict, profile_value: Any) -> bool | None:
    if profile_value is None:
        return None
    return bool(jsonLogic(_rule(kind, value), {"x": profile_value}))


def _render_value(kind: str, value: dict) -> str:
    if kind == "numeric_max":
        return f"Rs {value['amount']:,}"
    if kind == "category_in":
        return ", ".join(value["allowed"])
    return str(value)


def _render_actual(kind: str, profile_value: Any) -> str | None:
    if profile_value is None:
        return None
    if kind == "numeric_max":
        return f"Rs {profile_value:,}"
    return str(profile_value)


def evaluate(conditions: list[Condition], profile: dict) -> tuple[Verdict, list[ConditionResult]]:
    results: list[ConditionResult] = []
    any_missing = False
    any_conflict = False

    for c in conditions:
        profile_value = profile.get(c.var_name)

        if not c.sources:
            any_missing = True
            results.append(ConditionResult(
                condition_id=c.id, passed=None, human_text=c.human_text,
                actual=_render_actual(c.kind, profile_value),
                counterfactual="Not published on any official page we could fetch.",
            ))
            continue

        distinct_values = {_hashable(s.value) for s in c.sources}
        provenance = [s.provenance for s in c.sources]

        if len(distinct_values) > 1 and _sources_disagree(c):
            any_conflict = True
            # de-duplicate the real dict values (not just hashable keys) for rendering
            seen_keys = set()
            distinct_dicts = []
            for s in c.sources:
                k = _hashable(s.value)
                if k not in seen_keys:
                    seen_keys.add(k)
                    distinct_dicts.append(s.value)

            rendered = [_render_value(c.kind, v) for v in distinct_dicts]
            qualifies_under = [
                _render_value(c.kind, v) for v in distinct_dicts
                if _apply(c.kind, v, profile_value) is True
            ]
            fails_under = [
                _render_value(c.kind, v) for v in distinct_dicts
                if _apply(c.kind, v, profile_value) is False
            ]
            counterfactual = None
            if qualifies_under and fails_under:
                counterfactual = (
                    f"Under {' or '.join(qualifies_under)} you qualify. "
                    f"Under {' or '.join(fails_under)} you do not."
                )
            results.append(ConditionResult(
                condition_id=c.id, passed=None, human_text=c.human_text,
                actual=_render_actual(c.kind, profile_value),
                threshold=f"{' or '.join(rendered)} - sources disagree",
                provenance=provenance,
                counterfactual=counterfactual,
            ))
            continue

        value = c.sources[0].value
        passed = _apply(c.kind, value, profile_value)
        if passed is None:
            any_missing = True
        results.append(ConditionResult(
            condition_id=c.id, passed=passed, human_text=c.human_text,
            actual=_render_actual(c.kind, profile_value),
            threshold=_render_value(c.kind, value),
            provenance=provenance,
        ))

    if any_conflict:
        return Verdict.CONTRADICTORY_SOURCES, results
    if any(r.passed is False for r in results):
        return Verdict.NOT_ELIGIBLE, results
    if any_missing:
        return Verdict.INSUFFICIENT_DATA, results
    return Verdict.ELIGIBLE, results


def _sources_disagree(c: Condition) -> bool:
    """
    True when two live sources for the same condition publish different
    values. This is the Rs 3L / Rs 5L case: both stay live, both get shown,
    neither is picked as 'the' answer.
    """
    distinct = {_hashable(s.value) for s in c.sources}
    return len(distinct) > 1
