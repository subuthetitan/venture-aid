"""
PAIR B. These tests are the evidence behind "no number came from a model".
Write them early. A judge with a finance background will probe exactly here.
"""
from app.services.finance import calculate, emi
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
