"""
MERGE TEST (Pair A + Pair B integration).

finance.py's docstring says of SCHEME_TERMS:

    "URLs below are copied from shared/seed_schemes.json, which Pair A
     hand-verified against the live pages. Do not edit them here; that file
     is the source."

Nothing enforced that. Before the merge nothing could: Pair A's seed file and
Pair B's engine were being developed on branches that shared only the initial
commit. Now that both are in one tree, the claim is checkable, so it is checked.

If these fail, the two pairs disagree about what the government published. That
is a real discrepancy to resolve between them -- do NOT paper over it by
editing whichever side is redder.
"""
import json
from pathlib import Path

import pytest

from app.services.finance import SCHEME_TERMS

SEED_PATH = Path(__file__).parent.parent.parent / "shared" / "seed_schemes.json"


def _seed():
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def _by_id():
    return {s["id"]: s for s in _seed()["schemes"]}


def test_the_seed_file_is_where_both_pairs_think_it_is():
    assert SEED_PATH.is_file(), (
        f"{SEED_PATH} not found. services/seed_truth_layer.py resolves the same "
        "path the same way, so if this is missing Pair A's seed cannot run either."
    )


@pytest.mark.parametrize("scheme_id", sorted(SCHEME_TERMS))
def test_every_calculable_scheme_exists_in_the_seed_file(scheme_id):
    assert scheme_id in _by_id(), (
        f"finance.SCHEME_TERMS models '{scheme_id}' but shared/seed_schemes.json "
        "does not list it. The seed file is the source of truth for scheme identity."
    )


@pytest.mark.parametrize("scheme_id", sorted(SCHEME_TERMS))
def test_rate_and_ceiling_agree_with_the_seed_file(scheme_id):
    """The two numbers a wrong answer would put on a bank submission."""
    seed = _by_id().get(scheme_id)
    if seed is None:
        pytest.skip("covered by test_every_calculable_scheme_exists_in_the_seed_file")

    terms = SCHEME_TERMS[scheme_id]
    assert terms["rate"] == seed["rate_to_beneficiary"], (
        f"{scheme_id}: finance.py says {terms['rate']}%, "
        f"seed_schemes.json says {seed['rate_to_beneficiary']}%"
    )
    assert terms["max_loan"] == seed["max_loan"], (
        f"{scheme_id}: finance.py caps at Rs {terms['max_loan']:,}, "
        f"seed_schemes.json says Rs {seed['max_loan']:,}"
    )


def test_retired_schemes_are_never_calculable():
    """Pair A's recommender surfaces retired schemes on purpose (they still rank
    in search results). Pair B must not quote an EMI for one."""
    retired = {s["id"] for s in _seed()["schemes"] if s.get("status") == "retired"}
    assert retired, "seed file has no retired scheme; this test is asserting nothing"
    overlap = retired & set(SCHEME_TERMS)
    assert not overlap, f"retired scheme(s) present in SCHEME_TERMS: {sorted(overlap)}"


def test_a_scheme_the_recommender_can_return_but_finance_cannot_model_is_a_422():
    """The retired scheme is reachable from Pair A's /api/recommend response.

    If the frontend ever hands that scheme_id to /api/calculate it must get a
    clean 422, not a 500. This is the cross-pair case the UNKNOWN_SCHEME fix
    was for, now that Pair A's real recommender can actually emit that id.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    retired = next(s["id"] for s in _seed()["schemes"] if s.get("status") == "retired")
    res = TestClient(app).post(
        "/api/calculate", json={"scheme_id": retired, "project_cost": 100000}
    )
    assert res.status_code == 422
    assert res.json()["detail"]["error"] == "UNKNOWN_SCHEME"
