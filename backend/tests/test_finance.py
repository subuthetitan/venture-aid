"""
PAIR B. These tests are the evidence behind "no number came from a model".
Write them early. A judge with a finance background will probe exactly here.
"""
from app.services.finance import SCHEME_TERMS, calculate, emi
from decimal import Decimal


def test_emi_matches_standard_formula():
    # 1,00,000 at 12% for 12 months -> approx 8,884.88
    assert round(float(emi(Decimal(100000), 12.0, 12)), 2) == 8884.88


def test_moratorium_capitalises_interest():
    r = calculate("nsfdc.micro_credit", project_cost=125000)
    assert r.moratorium_months == 3
    assert r.schedule[0].month == 4          # repayment starts after moratorium
    assert r.total_interest > 0


def test_sanctionable_is_capped_at_scheme_ceiling():
    r = calculate("nsfdc.suvidha", project_cost=2000000)
    assert r.sanctionable_amount == 900000


def test_subsidy_delay_produces_a_note():
    r = calculate("nsfdc.suvidha", project_cost=500000,
                  subsidy_amount=100000, subsidy_delay_months=36)
    assert r.subsidy_note is not None


def test_own_contribution_reduces_sanctionable_below_ceiling():
    # 500000 - 50000 = 450000, well under suvidha's 900000 ceiling, so no capping.
    r = calculate("nsfdc.suvidha", project_cost=500000, own_contribution=50000)
    assert r.sanctionable_amount == 450000


def test_subsidy_amount_without_delay_produces_no_note():
    r = calculate("nsfdc.suvidha", project_cost=500000,
                  subsidy_amount=100000, subsidy_delay_months=0)
    assert r.subsidy_note is None


def test_provenance_is_always_computed():
    # Load-bearing honesty flag. If this ever reads 'generated', the demo claim
    # that no number came from a language model is false.
    for scheme_id in SCHEME_TERMS:
        r = calculate(scheme_id, project_cost=100000)
        assert r.provenance == "computed"


def test_schedule_amortises_to_zero_and_reconciles():
    r = calculate("nsfdc.suvidha", project_cost=900000)
    terms = SCHEME_TERMS["nsfdc.suvidha"]

    # One row per repayment month, numbered from the end of the moratorium.
    assert len(r.schedule) == terms["tenure"] - terms["moratorium"]
    assert r.schedule[0].month == terms["moratorium"] + 1
    assert r.schedule[-1].month == terms["tenure"]

    # The loan is fully repaid at the end.
    assert r.schedule[-1].closing_balance == 0.0

    # Totals are rounded once at output while rows round individually, so the
    # sum of the rows may drift by a few paise. Anything larger is a real bug.
    # The schedule's interest column covers the REPAYMENT period only, so it
    # reconciles against total_interest less the moratorium capitalisation.
    row_interest = sum(row.interest for row in r.schedule)
    assert abs(row_interest - (r.total_interest - r.moratorium_interest)) < 1.0
    assert abs(sum(row.emi for row in r.schedule) - r.total_repayment) < 1.0


def test_every_row_balances():
    # Each field is rounded independently, so these identities can drift by up
    # to 0.015 (three roundings of 0.005). Anything beyond that is a real bug.
    r = calculate("nsfdc.micro_credit", project_cost=125000)
    for row in r.schedule:
        assert abs(row.interest + row.principal - row.emi) <= 0.02
        assert abs(row.opening_balance - row.principal - row.closing_balance) <= 0.02


def test_moratorium_capitalisation_raises_the_repaid_principal():
    # Nothing is repaid during the moratorium, so total repayment must exceed
    # the sanctioned amount by more than simple interest on the flat balance.
    r = calculate("nsfdc.micro_credit", project_cost=125000)
    assert r.total_repayment > r.sanctionable_amount
    assert r.schedule[0].opening_balance > r.sanctionable_amount


def test_zero_rate_scheme_does_not_divide_by_zero():
    # Guards the r == 0 branch in emi(); no live scheme is at 0% today.
    assert emi(Decimal(120000), 0.0, 12) == Decimal(10000)


# ---------------------------------------------- hardening pass edge cases --
def test_project_cost_below_every_ceiling_is_not_capped():
    # 50,000 is under every scheme's max_loan, so nothing should be trimmed.
    for scheme_id in SCHEME_TERMS:
        r = calculate(scheme_id, project_cost=50000)
        assert r.sanctionable_amount == 50000


def test_project_cost_above_every_ceiling_is_capped_to_that_ceiling():
    for scheme_id, terms in SCHEME_TERMS.items():
        r = calculate(scheme_id, project_cost=50_000_000)
        assert r.sanctionable_amount == terms["max_loan"]


def test_own_contribution_equal_to_project_cost_gives_zero_not_a_loan():
    r = calculate("nsfdc.micro_credit", project_cost=100000, own_contribution=100000)
    assert r.sanctionable_amount == 0
    assert r.emi == 0.0
    assert r.total_interest == 0.0
    assert r.total_repayment == 0.0


def test_own_contribution_exceeding_project_cost_never_goes_negative():
    # REGRESSION: this previously produced sanctionable=-50000, emi=-1685.79
    # and total_repayment=-55631.05 -- a negative loan on a bank submission.
    r = calculate("nsfdc.micro_credit", project_cost=100000, own_contribution=150000)
    assert r.sanctionable_amount == 0
    assert r.emi >= 0
    assert r.total_interest >= 0
    assert r.total_repayment >= 0
    for row in r.schedule:
        assert row.opening_balance >= 0
        assert row.emi >= 0
        assert row.closing_balance >= 0


def test_no_money_field_is_ever_negative_across_a_sweep():
    # Broad guard: no combination of inputs should produce negative money.
    for scheme_id in SCHEME_TERMS:
        for cost in [0, 1000, 125000, 900000, 5_000_000]:
            for own in [0, 500, cost, cost + 100000]:
                r = calculate(scheme_id, project_cost=cost, own_contribution=own)
                assert r.sanctionable_amount >= 0
                assert r.emi >= 0
                assert r.total_interest >= 0
                assert r.total_repayment >= 0


def test_subsidy_note_requires_both_amount_and_delay():
    base = dict(scheme_id="nsfdc.suvidha", project_cost=500000)
    assert calculate(**base, subsidy_amount=100000, subsidy_delay_months=0).subsidy_note is None
    assert calculate(**base, subsidy_amount=0, subsidy_delay_months=36).subsidy_note is None
    assert calculate(**base, subsidy_amount=0, subsidy_delay_months=0).subsidy_note is None
    assert calculate(**base, subsidy_amount=100000, subsidy_delay_months=36).subsidy_note is not None


def test_subsidy_note_makes_no_uncited_factual_claim():
    """The note must state only the computed figure and the user's own scenario.

    It previously ended "One documented case ran three years." -- an assertion
    about a real event with no citation anywhere in the repo (docs/SOURCE_DATABASE.csv
    row TIME-01). This text is shown to applicants, so it must not re-appear.
    """
    r = calculate("nsfdc.suvidha", project_cost=500000,
                  subsidy_amount=100000, subsidy_delay_months=36)
    note = r.subsidy_note
    assert note is not None
    for banned in ("documented case", "ran three years", "three years"):
        assert banned not in note.lower(), f"uncited factual claim back in note: {banned!r}"
    # The computed part must survive.
    assert "100,000" in note and "months late" in note


# ------------------------------------------------- bug-fix regression pass --
def test_total_interest_includes_moratorium_capitalisation():
    """REGRESSION: total_interest used to be the schedule sum only.

    On a Rs 5,00,000 Suvidha loan that silently omitted Rs 20,336 of interest
    capitalised during the 6-month moratorium, and the response contradicted
    itself: sanctionable + total_interest != total_repayment. This is the one
    feature whose whole claim is that every number is arithmetic we can show,
    so an understated cost of borrowing is the worst defect it can carry.
    """
    for scheme_id in SCHEME_TERMS:
        r = calculate(scheme_id, project_cost=500000)
        if r.sanctionable_amount == 0:
            continue
        assert r.moratorium_interest > 0
        # The identity that must hold for any amortising loan.
        assert abs(
            (r.sanctionable_amount + r.total_interest) - r.total_repayment
        ) < 1.0, f"{scheme_id} does not reconcile"
        # And the moratorium interest is genuinely absent from the rows.
        rows = sum(row.interest for row in r.schedule)
        assert abs(r.total_interest - r.moratorium_interest - rows) < 1.0


def test_moratorium_interest_is_zero_when_there_is_no_loan():
    r = calculate("nsfdc.suvidha", project_cost=100000, own_contribution=100000)
    assert r.moratorium_interest == 0.0
    assert r.total_interest == 0.0


def test_negative_own_contribution_cannot_inflate_the_loan():
    """REGRESSION: own_contribution=-50000 on a Rs 1,00,000 project sanctioned
    Rs 1,50,000 -- a larger loan than the project needs, on a bank submission.
    """
    r = calculate("nsfdc.suvidha", project_cost=100000, own_contribution=-50000)
    assert r.sanctionable_amount == 100000


def test_negative_project_cost_is_clamped_not_propagated():
    r = calculate("nsfdc.suvidha", project_cost=-100000)
    assert r.sanctionable_amount == 0
    assert r.emi == 0.0
    assert r.total_repayment == 0.0


def test_unknown_scheme_raises_a_typed_error_not_a_bare_keyerror():
    """REGRESSION: a bad scheme_id escaped as KeyError -> HTTP 500.

    Utkarsh is the realistic trigger: it is deliberately absent from
    SCHEME_TERMS, so anyone wiring it up from Pair A's seed data hits this.
    """
    import pytest

    from app.services.finance import UnknownScheme

    with pytest.raises(UnknownScheme):
        calculate("nsfdc.utkarsh", project_cost=100000)


def test_emi_with_no_repayment_months_returns_zero_not_a_crash():
    # Guards a scheme whose moratorium equals its tenure. Both branches of
    # emi() used to divide by zero here.
    assert emi(Decimal(100000), 8.0, 0) == Decimal(0)
    assert emi(Decimal(100000), 0.0, 0) == Decimal(0)
    assert emi(Decimal(0), 8.0, 12) == Decimal(0)
