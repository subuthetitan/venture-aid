"""
PAIR A. These tests are the evidence behind the four-state verdict and the
contradiction reveal - same spirit as tests/test_finance.py for Pair B.

Runs against an in-memory SQLite DB (not the real Postgres) so this suite
has no infra dependency: `pytest backend/tests/test_eligibility.py` just works.
"""
import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db import Base, get_db
from app.main import app
from app.services.seed_truth_layer import seed


# SQLite only auto-increments a PK column with exact type affinity INTEGER
# (its ROWID-alias rule) - BigInteger autoincrement PKs (fine on the real
# Postgres DB) need this compile-time swap to work in an in-memory SQLite
# test DB. Test-harness-only; does not touch the real schema in models.py.
@compiles(BigInteger, "sqlite")
def _big_int_as_integer_on_sqlite(type_, compiler, **kw):
    return "INTEGER"


@pytest.fixture()
def client():
    # StaticPool: an in-memory SQLite DB is otherwise per-connection, so every
    # new session in override_get_db() would see an empty database. StaticPool
    # keeps every connection on the same underlying in-memory DB for this test.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(engine)

    db = TestingSession()
    seed(db)
    db.close()

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _profile(**overrides):
    base = dict(family_income=250000, caste_category="SC",
                state_code="TS", district_code="TS01")
    base.update(overrides)
    return base


def test_the_reveal_income_between_thresholds_is_contradictory(client):
    """The exact demo moment: Rs 4,20,000 sits between Rs 3L and Rs 5L."""
    resp = client.post("/api/recommend", json=_profile(family_income=420000))
    assert resp.status_code == 200
    body = resp.json()

    suvidha = next(m for m in body["matches"] if m["scheme_id"] == "nsfdc.suvidha")
    assert suvidha["verdict"] == "CONTRADICTORY_SOURCES"
    assert suvidha["disagreement_note"] is not None

    income_condition = next(c for c in suvidha["conditions"] if c["condition_id"] == "family_income_ceiling")
    assert income_condition["passed"] is None
    urls = {p["source_url"] for p in income_condition["provenance"]}
    assert "https://nsfdc.nic.in/about-us-3" in urls
    assert "https://nsfdc.nic.in/en/how-to-apply" in urls


def test_low_income_clearly_eligible_on_suvidha(client):
    """Rs 2,50,000 is under BOTH disputed ceilings - still surfaced as a live disagreement,
    not silently resolved, because the plan says CONTRADICTORY_SOURCES is a first-class
    verdict, not something to paper over even when the applicant would pass either way."""
    resp = client.post("/api/recommend", json=_profile(family_income=250000))
    body = resp.json()
    suvidha = next(m for m in body["matches"] if m["scheme_id"] == "nsfdc.suvidha")
    assert suvidha["verdict"] == "CONTRADICTORY_SOURCES"


def test_age_criteria_is_honestly_insufficient_data(client):
    resp = client.post("/api/recommend", json=_profile(family_income=100000))
    body = resp.json()
    suvidha = next(m for m in body["matches"] if m["scheme_id"] == "nsfdc.suvidha")
    age_condition = next(c for c in suvidha["conditions"] if c["condition_id"] == "age_criteria")
    assert age_condition["passed"] is None
    assert age_condition["provenance"] == []
    assert "not published" in age_condition["counterfactual"].lower()


def test_scheme_with_no_income_data_is_insufficient_not_invented(client):
    """nsfdc.micro_credit has a verified caste condition but NO verified income
    ceiling in the seed file. The engine must say so, not guess a number."""
    resp = client.post("/api/recommend", json=_profile(family_income=250000))
    body = resp.json()
    micro = next(m for m in body["matches"] if m["scheme_id"] == "nsfdc.micro_credit")
    income_condition = next(c for c in micro["conditions"] if c["condition_id"] == "family_income_ceiling")
    assert income_condition["passed"] is None
    assert income_condition["provenance"] == []
    assert micro["verdict"] == "INSUFFICIENT_DATA"


def test_wrong_caste_is_not_eligible(client):
    resp = client.post("/api/recommend", json=_profile(family_income=250000, caste_category="OBC"))
    body = resp.json()
    micro = next(m for m in body["matches"] if m["scheme_id"] == "nsfdc.micro_credit")
    assert micro["verdict"] == "NOT_ELIGIBLE"


def test_retired_scheme_is_flagged_not_silently_dropped(client):
    resp = client.post("/api/recommend", json=_profile(family_income=250000))
    body = resp.json()
    ids = {m["scheme_id"] for m in body["matches"]}
    assert "nsfdc.term_loan" in ids
    retired = next(m for m in body["matches"] if m["scheme_id"] == "nsfdc.term_loan")
    assert retired["verdict"] == "NOT_ELIGIBLE"
    assert "retired" in retired["conditions"][0]["human_text"].lower()


def test_truth_layer_contradictions_endpoint_surfaces_the_same_reveal(client):
    resp = client.get("/api/truth/contradictions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["scheme_id"] == "nsfdc.suvidha"
    assert body[0]["field"] == "family_income_ceiling"
    amounts = {p["value"]["amount"] for p in body[0]["positions"]}
    assert amounts == {500000, 300000}


# --------------------------------------------- integration-pass regression --
def test_non_money_conditions_are_not_rendered_as_rupees():
    """REGRESSION: age_criteria is a `numeric_max` like the income ceiling, so
    the renderer keyed off `kind` printed an applicant aged 30 as "Rs 30".

    That string is displayed verbatim on the Recommender screen, so it is a
    user-visible defect, not a cosmetic one. `unit` is the correct axis: money
    is not the only thing you can put a ceiling on.
    """
    from app.schemas import Provenance
    from app.services.eligibility import Condition, ConditionSource, evaluate

    prov = Provenance(source_url="https://example.gov.in/x",
                      source_authority="NSFDC", observed_at="2026-09-03")

    age = Condition(id="age_criteria", kind="numeric_max", var_name="age",
                    human_text="Age limit", unit="years",
                    sources=[ConditionSource(value={"amount": 55}, provenance=prov)])
    income = Condition(id="family_income_ceiling", kind="numeric_max",
                       var_name="family_income", human_text="Income ceiling",
                       sources=[ConditionSource(value={"amount": 300000}, provenance=prov)])

    _, results = evaluate([age, income], {"age": 30, "family_income": 250000})
    by_id = {r.condition_id: r for r in results}

    assert by_id["age_criteria"].actual == "30 years"
    assert by_id["age_criteria"].threshold == "55 years"
    assert "Rs" not in by_id["age_criteria"].actual
    assert "Rs" not in by_id["age_criteria"].threshold

    # Money conditions must be unchanged -- `unit` defaults to 'inr'.
    assert by_id["family_income_ceiling"].actual == "Rs 250,000"
    assert by_id["family_income_ceiling"].threshold == "Rs 300,000"


def test_recommend_tags_a_unit_for_every_field_spec():
    """Every field spec must carry a unit, so a new condition cannot silently
    inherit rupee formatting the way age_criteria did."""
    import inspect

    from app.routers import recommend

    src = inspect.getsource(recommend._conditions_for_scheme)
    assert '"years"' in src and '"inr"' in src, "field_specs lost its unit column"
