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
    assert abs(sum(row.interest for row in r.schedule) - r.total_interest) < 1.0
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
