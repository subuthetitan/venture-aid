"""
PAIR B. Pure functions. No LLM, no network, no database.

This module is why you can say on stage: "no number in this document was
produced by a language model." Keep it that way. Tests in tests/test_finance.py.
"""
from decimal import ROUND_HALF_UP, Decimal

from app.schemas import CalculateResponse, ScheduleRow

# Verified from nsfdc.nic.in scheme pages. Rate is what the SCA charges the
# beneficiary, not what NSFDC charges the SCA.
SCHEME_TERMS = {
    # source: nsfdc.nic.in/en/suvidha
    "nsfdc.suvidha":          {"rate": 8.0, "tenure": 60, "moratorium": 6, "max_loan": 900000},
    # source: nsfdc.nic.in/en/micro-credit-finance
    "nsfdc.micro_credit":     {"rate": 6.5, "tenure": 36, "moratorium": 3, "max_loan": 125000},
    # source: nsfdc.nic.in/en/mahila-samriddhi-yojana
    "nsfdc.mahila_samriddhi": {"rate": 6.0, "tenure": 36, "moratorium": 3, "max_loan": 125000},
    # source: nsfdc.nic.in/en/laghu-vyavsay-yojana
    "nsfdc.laghu_vyavsay":    {"rate": 6.0, "tenure": 72, "moratorium": 6, "max_loan": 200000},
    # Utkarsh deliberately absent: NSFDC's own pages contradict each other on
    # whether Rs 10-50L is loan amount or project cost, and no rate is published.
}


def _q(x: Decimal) -> float:
    return float(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def emi(principal: Decimal, annual_rate: float, months: int) -> Decimal:
    r = Decimal(str(annual_rate)) / Decimal(1200)
    if r == 0:
        return principal / months
    factor = (1 + r) ** months
    return principal * r * factor / (factor - 1)


def calculate(scheme_id: str, project_cost: int, own_contribution: int = 0,
              subsidy_amount: int = 0, subsidy_delay_months: int = 0) -> CalculateResponse:
    terms = SCHEME_TERMS[scheme_id]
    sanctionable = min(project_cost - own_contribution, terms["max_loan"])
    principal = Decimal(sanctionable)

    # Interest accrues during the moratorium; only principal repayment is deferred.
    for _ in range(terms["moratorium"]):
        principal += principal * Decimal(str(terms["rate"])) / Decimal(1200)

    repay_months = terms["tenure"] - terms["moratorium"]
    monthly = emi(principal, terms["rate"], repay_months)

    schedule, balance, total_interest = [], principal, Decimal(0)
    for m in range(1, repay_months + 1):
        interest = balance * Decimal(str(terms["rate"])) / Decimal(1200)
        princ = monthly - interest
        total_interest += interest
        schedule.append(ScheduleRow(
            month=m + terms["moratorium"],
            opening_balance=_q(balance), interest=_q(interest),
            principal=_q(princ), emi=_q(monthly),
            closing_balance=_q(max(balance - princ, Decimal(0))),
        ))
        balance -= princ

    note = None
    if subsidy_amount and subsidy_delay_months:
        extra = _q(monthly * subsidy_delay_months)
        note = (f"If the Rs {subsidy_amount:,} subsidy arrives {subsidy_delay_months} "
                f"months late, you repay roughly Rs {extra:,.0f} before it lands. "
                f"One documented case ran three years.")

    return CalculateResponse(
        sanctionable_amount=int(sanctionable),
        interest_rate=terms["rate"],
        tenure_months=terms["tenure"],
        moratorium_months=terms["moratorium"],
        emi=_q(monthly),
        total_interest=_q(total_interest),
        total_repayment=_q(monthly * repay_months),
        schedule=schedule,
        subsidy_note=note,
        # Load-bearing honesty flag: every number above came from arithmetic in
        # this file. Never set this to 'generated'.
        provenance="computed",
    )
