"""
PAIR B. Scheme-selection tests for Sanction-Ready.

The gender gate is the reason this file exists: recommending a women-only
scheme to an applicant who cannot receive it sends someone to an SCA counter
to be turned away. It fails closed, and these tests pin that behaviour down.
"""
import pytest

from app.routers.readiness import (WOMEN_ONLY_SCHEMES, _is_eligible_scheme,
                                   _pick_scheme)
from app.services import finance

WOMEN_ONLY = "nsfdc.mahila_samriddhi"


def test_the_women_only_set_matches_a_real_scheme():
    # Guards against a typo silently disabling the whole gate.
    for scheme_id in WOMEN_ONLY_SCHEMES:
        assert scheme_id in finance.SCHEME_TERMS


# ------------------------------------------------------- eligibility gate --
@pytest.mark.parametrize("gender", ["female", "Female", "FEMALE", "f", "woman"])
def test_women_only_scheme_is_eligible_for_female_applicants(gender):
    assert _is_eligible_scheme(WOMEN_ONLY, gender) is True


@pytest.mark.parametrize("gender", ["male", "other", "", "   ", None, "unknown"])
def test_women_only_scheme_is_excluded_for_everyone_else(gender):
    # Fails closed, including when gender was never collected.
    assert _is_eligible_scheme(WOMEN_ONLY, gender) is False


@pytest.mark.parametrize("gender", ["female", "male", None])
def test_unrestricted_schemes_are_eligible_regardless_of_gender(gender):
    for scheme_id in finance.SCHEME_TERMS:
        if scheme_id not in WOMEN_ONLY_SCHEMES:
            assert _is_eligible_scheme(scheme_id, gender) is True


# ---------------------------------------------------------- scheme choice --
def test_male_applicant_is_never_routed_to_a_women_only_scheme():
    for cost in [50000, 85000, 125000, 210000, 2000000]:
        assert _pick_scheme(cost, "male") not in WOMEN_ONLY_SCHEMES


def test_unspecified_gender_is_never_routed_to_a_women_only_scheme():
    # The regression this whole change exists to prevent.
    for cost in [50000, 85000, 125000, 210000, 2000000]:
        assert _pick_scheme(cost, None) not in WOMEN_ONLY_SCHEMES


def test_female_applicant_can_receive_the_women_only_scheme():
    # At 6.0% it ties with laghu_vyavsay; both are legitimate for her, but she
    # must not be excluded from it.
    assert _pick_scheme(85000, "female") == WOMEN_ONLY


def test_gender_never_makes_the_recommended_rate_worse_for_women():
    # A woman should never be offered a costlier scheme than a man for the
    # same project cost.
    for cost in [50000, 85000, 125000, 210000, 900000]:
        female = finance.SCHEME_TERMS[_pick_scheme(cost, "female")]["rate"]
        male = finance.SCHEME_TERMS[_pick_scheme(cost, "male")]["rate"]
        assert female <= male


def test_chosen_scheme_covers_the_project_cost_when_one_can():
    for gender in ["female", "male", None]:
        for cost in [50000, 85000, 125000]:
            chosen = finance.SCHEME_TERMS[_pick_scheme(cost, gender)]
            assert chosen["max_loan"] >= cost


def test_oversized_project_falls_back_to_the_largest_eligible_ceiling():
    # 20L exceeds every ceiling; pick the biggest one we are allowed to use.
    for gender in ["female", "male", None]:
        chosen = _pick_scheme(2000000, gender)
        eligible = [s for s in finance.SCHEME_TERMS
                    if _is_eligible_scheme(s, gender)]
        assert chosen == max(eligible,
                             key=lambda s: finance.SCHEME_TERMS[s]["max_loan"])


def test_scheme_choice_is_deterministic():
    assert len({_pick_scheme(85000, "male") for _ in range(20)}) == 1


# ---------------------------------------------- hardening pass edge cases --
def test_gender_matching_tolerates_case_and_surrounding_whitespace():
    # The schema deliberately does NOT constrain gender to an enum, so the
    # gate has to absorb whatever the intake form emits.
    for value in ["female", "Female", "FEMALE", "  female  ", "\tFemale\n", "F", "Woman"]:
        assert _is_eligible_scheme(WOMEN_ONLY, value) is True, value
    for value in ["", "   ", None, "male", "Male", "other", "unknown", "femalex"]:
        assert _is_eligible_scheme(WOMEN_ONLY, value) is False, value


def test_no_scheme_covers_the_project_cost_falls_back_without_crashing():
    # 5 crore exceeds every ceiling. Must still return a real scheme id --
    # the shortfall then shows as project_cost > sanctionable_amount rather
    # than an exception or an empty recommendation.
    for gender in ["female", "male", None]:
        chosen = _pick_scheme(50_000_000, gender)
        assert chosen in finance.SCHEME_TERMS
        assert _is_eligible_scheme(chosen, gender)


# --------------------------------------------------- end-to-end via route --
def _client():
    from fastapi.testclient import TestClient

    from app.main import app
    return TestClient(app)


PROFILE = {"family_income": 0, "state_code": "KA", "district_code": ""}


def test_explicit_activity_id_wins_over_a_conflicting_transcript():
    # ReadinessRequest carries both fields as optional. An explicit id is a
    # deliberate operator/user choice (the frontend's recovery chips send one),
    # so it must override whatever the keyword classifier would have guessed.
    r = _client().post("/api/readiness", json={
        "transcript": "I want to start a dairy with buffaloes",
        "activity_id": "tailoring_unit",
        "profile": PROFILE,
    })
    assert r.status_code == 200
    assert r.json()["activity_id"] == "tailoring_unit"


def test_activity_id_alone_is_enough_and_empty_transcript_does_not_override_it():
    client = _client()
    for body in ({"activity_id": "goat_rearing", "profile": PROFILE},
                 {"activity_id": "goat_rearing", "transcript": "", "profile": PROFILE}):
        r = client.post("/api/readiness", json=body)
        assert r.status_code == 200
        assert r.json()["activity_id"] == "goat_rearing"


def test_neither_transcript_nor_activity_id_is_a_clean_422():
    r = _client().post("/api/readiness", json={"profile": PROFILE})
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "UNRECOGNIZED_ACTIVITY"


def test_pdf_failure_never_fails_the_report():
    # The router is fail-open by design: an unexpected PDF error must still
    # return the JSON report with pdf_url null, not a 500.
    from app.services import pdf_generator

    real = pdf_generator.generate_pdf

    def boom(*args, **kwargs):
        raise RuntimeError("simulated PDF explosion")

    pdf_generator.generate_pdf = boom
    try:
        r = _client().post("/api/readiness",
                           json={"activity_id": "tailoring_unit", "profile": PROFILE})
    finally:
        pdf_generator.generate_pdf = real

    assert r.status_code == 200
    assert r.json()["pdf_url"] is None
    assert r.json()["total_project_cost"] > 0
