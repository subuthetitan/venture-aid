"""
PAIR B. Pure functions. No LLM, no network, no database.

This module is why you can say on stage: "no number in this document was
produced by a language model." Keep it that way. Tests in tests/test_finance.py.
"""
from decimal import ROUND_HALF_UP, Decimal

from app.schemas import CalculateResponse, ScheduleRow

# Verified from nsfdc.nic.in scheme pages. Rate is what the SCA charges the
# beneficiary, not what NSFDC charges the SCA.
# URLs below are copied from shared/seed_schemes.json, which Pair A hand-verified
# against the live pages on 2026-09-03. Do not edit them here; that file is the source.
SCHEME_TERMS = {
    # source: https://nsfdc.nic.in/en/suvidha-loan
    "nsfdc.suvidha":          {"rate": 8.0, "tenure": 60, "moratorium": 6, "max_loan": 900000},
    # source: https://nsfdc.nic.in/en/micro-credit-finance
    "nsfdc.micro_credit":     {"rate": 6.5, "tenure": 36, "moratorium": 3, "max_loan": 125000},
    # source: https://nsfdc.nic.in/en/mahila-samriddhi-yojana
    "nsfdc.mahila_samriddhi": {"rate": 6.0, "tenure": 36, "moratorium": 3, "max_loan": 125000},
    # source: https://nsfdc.nic.in/en/laghu-vyavsay-yojana
    "nsfdc.laghu_vyavsay":    {"rate": 6.0, "tenure": 72, "moratorium": 6, "max_loan": 200000},
    # Utkarsh deliberately absent: NSFDC's own pages contradict each other on
    # whether Rs 10-50L is loan amount or project cost, and no rate is published.
}


class UnknownScheme(KeyError):
    """calculate() was handed a scheme_id that is not in SCHEME_TERMS.

    Its own class so the router can turn it into a 422 listing the schemes we
    do support, instead of letting a bare KeyError become a 500. Utkarsh is the
    realistic trigger: it is deliberately absent from SCHEME_TERMS, so anyone
    wiring it up from Pair A's seed data hits this.
    """


def _q(x: Decimal) -> float:
    return float(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def emi(principal: Decimal, annual_rate: float, months: int) -> Decimal:
    """Equated monthly instalment on a reducing balance.

    `months` is the number of REPAYMENT months, which for our schemes is
    tenure - moratorium. Returns 0 when there is nothing to repay: a
    zero-length schedule used to raise ZeroDivisionError on both branches and
    take the whole endpoint down with a 500.
    """
    if months <= 0 or principal <= 0:
        return Decimal(0)
    r = Decimal(str(annual_rate)) / Decimal(1200)
    if r == 0:
        return principal / months
    factor = (1 + r) ** months
    return principal * r * factor / (factor - 1)


def calculate(scheme_id: str, project_cost: int, own_contribution: int = 0,
              subsidy_amount: int = 0, subsidy_delay_months: int = 0) -> CalculateResponse:
    try:
        terms = SCHEME_TERMS[scheme_id]
    except KeyError:
        raise UnknownScheme(scheme_id) from None

    # Negative money is not a scenario, it is malformed input. The API layer
    # rejects it with a 422 (ge=0 on CalculateRequest), but calculate() is also
    # called directly by readiness.py and by tests, so it clamps here too. A
    # negative own_contribution previously INFLATED the loan -- Rs 1,00,000 of
    # project cost with own_contribution=-50,000 sanctioned Rs 1,50,000.
    project_cost = max(project_cost, 0)
    own_contribution = max(own_contribution, 0)
    subsidy_amount = max(subsidy_amount, 0)
    subsidy_delay_months = max(subsidy_delay_months, 0)

    # Clamp at zero. When own_contribution covers the whole project the
    # applicant needs no loan; without the clamp this went NEGATIVE and the
    # response reported a negative sanctionable amount, a negative EMI and a
    # negative total repayment -- numbers that would have gone onto a bank
    # submission. A fully self-funded project is sanctionable=0, not a debt
    # owed to the applicant.
    sanctionable = max(min(project_cost - own_contribution, terms["max_loan"]), 0)
    principal = Decimal(sanctionable)

    # Interest accrues during the moratorium; only principal repayment is deferred.
    for _ in range(terms["moratorium"]):
        principal += principal * Decimal(str(terms["rate"])) / Decimal(1200)

    # Interest capitalised before the first instalment. This is real money the
    # applicant owes and it is NOT in any schedule row, because the schedule
    # only starts once repayment does.
    moratorium_interest = principal - Decimal(sanctionable)

    repay_months = terms["tenure"] - terms["moratorium"]
    monthly = emi(principal, terms["rate"], repay_months)

    schedule, balance, repayment_interest = [], principal, Decimal(0)
    for m in range(1, repay_months + 1):
        interest = balance * Decimal(str(terms["rate"])) / Decimal(1200)
        princ = monthly - interest
        repayment_interest += interest
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
        # The figure below is computed. The sentence that used to follow it --
        # "One documented case ran three years." -- was an uncited factual claim
        # about a real event and has been removed: see docs/SOURCE_DATABASE.csv
        # row TIME-01. The delay is framed as the applicant's own hypothetical
        # (they chose subsidy_delay_months), not as something we assert happened.
        note = (f"If the Rs {subsidy_amount:,} subsidy arrives {subsidy_delay_months} "
                f"months late, you repay roughly Rs {extra:,.0f} before it lands.")

    # BUG FIX: total_interest used to be the sum of the schedule rows only,
    # which SILENTLY DROPPED the interest capitalised during the moratorium --
    # Rs 20,336 on a Rs 5,00,000 Suvidha loan. The response then failed its own
    # identity: sanctionable + total_interest != total_repayment. On the one
    # feature whose whole claim is "every number here is arithmetic we can
    # show you", an understated cost of borrowing is the worst possible defect.
    # total_interest is now the FULL cost of borrowing. moratorium_interest is
    # reported separately so the UI can explain why the schedule's interest
    # column sums to less than this figure.
    total_interest = moratorium_interest + repayment_interest

    return CalculateResponse(
        sanctionable_amount=int(sanctionable),
        interest_rate=terms["rate"],
        tenure_months=terms["tenure"],
        moratorium_months=terms["moratorium"],
        emi=_q(monthly),
        total_interest=_q(total_interest),
        moratorium_interest=_q(moratorium_interest),
        total_repayment=_q(monthly * repay_months),
        schedule=schedule,
        subsidy_note=note,
        # Load-bearing honesty flag: every number above came from arithmetic in
        # this file. Never set this to 'generated'.
        provenance="computed",
    )
