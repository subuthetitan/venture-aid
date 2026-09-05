"""
FROZEN CONTRACTS. Agreed before hour 0, changed only by integrator consensus.

The frontend builds against these shapes from minute one, because every router
returns a valid fixture in this shape from day zero. Nobody stubs anything by
hand; nobody waits for another pair.
"""
from enum import Enum

from pydantic import BaseModel, Field


# ------------------------------------------------------- shared primitives --
class Provenance(BaseModel):
    source_url: str
    source_authority: str            # 'NSFDC' | 'MoSJE' | 'State:TS'
    observed_at: str                 # ISO8601
    effective_from: str | None = None


class Verdict(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    CONTRADICTORY_SOURCES = "CONTRADICTORY_SOURCES"   # first-class, not an error
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"           # rule not published anywhere


# ------------------------------------------------------- PAIR A: recommend --
class ApplicantProfile(BaseModel):
    family_income: int
    caste_category: str = "SC"
    state_code: str
    district_code: str
    activity: str | None = None
    amount_needed: int | None = None
    age: int | None = None
    # Gender-restricted schemes (e.g. Mahila Samriddhi Yojana) may only be
    # recommended to applicants who qualify. Optional and defaulted so every
    # existing caller keeps working; when it is None, gender-restricted
    # schemes are EXCLUDED rather than assumed. Expected: 'female' | 'male' |
    # 'other', matched case-insensitively by consumers.
    gender: str | None = None


class ConditionResult(BaseModel):
    condition_id: str                # 'income_ceiling'
    passed: bool | None              # None when INSUFFICIENT_DATA
    human_text: str
    actual: str | None = None
    threshold: str | None = None
    provenance: list[Provenance] = Field(default_factory=list)
    counterfactual: str | None = None


class SchemeMatch(BaseModel):
    scheme_id: str
    scheme_name: str
    verdict: Verdict
    conditions: list[ConditionResult]
    max_loan: int | None = None
    interest_rate: float | None = None
    disagreement_note: str | None = None   # set when verdict is CONTRADICTORY_SOURCES


class RecommendResponse(BaseModel):
    matches: list[SchemeMatch]
    seeded: bool = True                    # honesty flag surfaced in the UI


# ------------------------------------------------------- PAIR B: calculate --
class CalculateRequest(BaseModel):
    scheme_id: str
    project_cost: int
    own_contribution: int = 0
    subsidy_amount: int = 0
    subsidy_delay_months: int = 0          # the differentiator


class ScheduleRow(BaseModel):
    month: int
    opening_balance: float
    interest: float
    principal: float
    emi: float
    closing_balance: float


class CalculateResponse(BaseModel):
    sanctionable_amount: int
    interest_rate: float
    tenure_months: int
    moratorium_months: int
    emi: float
    total_interest: float
    total_repayment: float
    schedule: list[ScheduleRow]
    subsidy_note: str | None = None
    provenance: str = "computed"           # never 'generated'


# ------------------------------------------------------- PAIR B: readiness --
class ReadinessRequest(BaseModel):
    transcript: str | None = None
    activity_id: str | None = None
    language: str = "hi"
    profile: ApplicantProfile


class ProjectReport(BaseModel):
    activity_id: str
    activity_label: str
    narrative: str                         # LLM-written
    capex_items: list[dict]                # computed
    total_project_cost: int                # computed
    recommended_scheme_id: str
    finance: CalculateResponse             # computed
    break_even_months: int                 # computed
    document_checklist: list[str]
    pdf_url: str | None = None


# --------------------------------------------------------- PAIR C: locator --
class ChannelOut(BaseModel):
    id: str
    kind: str
    name: str
    district_code: str
    address: str | None = None
    phone: str | None = None
    lat: float | None = None
    lon: float | None = None


class RouteOut(BaseModel):
    distance_km: float
    duration_min: float
    geometry: dict                         # GeoJSON LineString
    provider: str                          # 'mappls' | 'fixture'


class ReachabilityCell(BaseModel):
    district_code: str
    state_code: str
    has_sca: bool
    channel_count: int
    note: str | None = None                # 'No SCA in this state'


# ---------------------------------------------------------- PAIR C: ledger --
class LedgerCell(BaseModel):
    district_code: str
    applications: int
    median_days_to_sanction: int | None
    suppressed: bool = False               # k-anonymity: fewer than 5


class LedgerResponse(BaseModel):
    cells: list[LedgerCell]
    data_source: str = "synthetic"         # printed on the chart, not a footnote
    caveat: str = "Prototype data. Self-reported and self-selected."
