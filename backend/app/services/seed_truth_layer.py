"""
PAIR A. Loads shared/seed_schemes.json (the frozen, hand-verified contract)
into the real `scheme` and `rule_version` tables.

Run once after `docker compose up` brings up Postgres and Alembic has run
migration 0001:

    python -m app.services.seed_truth_layer

Idempotent: safe to re-run. Deletes and re-inserts rather than upserting,
because these are hand-verified fixture rows, not live application data -
there's nothing a re-run could destroy that isn't already in this file.

Value shape convention for rule_version.value (documented once, here):
  - field="family_income_ceiling" -> {"amount": <int>}
  - field="caste_category"        -> {"allowed": [<str>, ...]}
  - field="age_criteria"          -> not seeded at all for any scheme below;
    that's not an oversight, it's what "unpublished" in the seed file means.
    An eligibility Condition with zero sources becomes INSUFFICIENT_DATA
    automatically - see app/services/eligibility.py.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import RuleVersion, Scheme

SEED_PATH = Path(__file__).parent.parent.parent.parent / "shared" / "seed_schemes.json"


def _parse_dt(date_str: str) -> datetime:
    """Accepts both '2026-09-03' and '2026-09-03T00:00:00Z'."""
    if "T" in date_str:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return datetime(*map(int, date_str.split("-")), tzinfo=timezone.utc)


def load_seed_data() -> dict:
    return json.loads(SEED_PATH.read_text())


def seed(db: Session) -> None:
    data = load_seed_data()

    db.query(RuleVersion).delete()
    db.query(Scheme).delete()

    for s in data["schemes"]:
        db.add(Scheme(
            id=s["id"], name=s["name"], corporation=s["corporation"], status=s["status"],
        ))
    db.flush()  # scheme rows must exist before rule_version FKs reference them

    observed_at_default = _parse_dt("2026-09-03")

    # caste_category — one row per active scheme that has a source_url to cite.
    # Every active NSFDC scheme in this file is SC-only by corporation mandate.
    for s in data["schemes"]:
        if s["status"] != "active" or "source_url" not in s:
            continue
        db.add(RuleVersion(
            scheme_id=s["id"], field="caste_category", value={"allowed": ["SC"]},
            source_url=s["source_url"], source_authority=s["corporation"],
            extracted_by="human", extraction_confidence=1.0,
            observed_at=observed_at_default, verified_by_human=True,
        ))

    # family_income_ceiling — only where shared/seed_schemes.json actually
    # gives us verified numbers. Right now that's only the contradiction
    # block for nsfdc.suvidha. No invented thresholds for the other schemes.
    for c in data.get("contradictions", []):
        for pos in c["positions"]:
            db.add(RuleVersion(
                scheme_id=c["scheme_id"], field=c["field"], value={"amount": pos["amount"]},
                source_url=pos["source_url"], source_authority=pos["authority"],
                extracted_by="human", extraction_confidence=1.0,
                effective_from=(datetime.fromisoformat(pos["effective_from"]).date()
                                if pos.get("effective_from") else None),
                observed_at=_parse_dt(pos["observed_at"]),
                verified_by_human=True,
            ))

    db.commit()


def main():
    db = SessionLocal()
    try:
        seed(db)
        print(f"Seeded {db.query(Scheme).count()} schemes, "
              f"{db.query(RuleVersion).count()} rule_version rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
