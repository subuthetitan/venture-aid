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
