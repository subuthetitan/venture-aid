"""Loads Pair C fixtures into the database. Idempotent - safe to re-run."""
import json
from datetime import date, datetime
from pathlib import Path

from app.db import SessionLocal
from app.models import ApplicationMilestone, Channel

HERE = Path(__file__).parent


def _read(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def load() -> None:
    db = SessionLocal()
    try:
        db.query(ApplicationMilestone).delete()
        db.query(Channel).delete()
        db.commit()

        payload = _read("channels.json")
        channels = payload["channels"] if isinstance(payload, dict) else payload
        for row in channels:
            # Fields prefixed with _ are provenance documentation, not columns.
            clean = {k: v for k, v in row.items() if not k.startswith("_")}
            db.add(Channel(**clean))

        for row in _read("ledger_milestones.json"):
            row["occurred_on"] = date.fromisoformat(row["occurred_on"])
            row["reported_at"] = datetime.fromisoformat(row["reported_at"])
            db.add(ApplicationMilestone(**row))

        db.commit()
        print(f"Loaded {len(channels)} channels and {len(_read('ledger_milestones.json'))} milestones.")
    finally:
        db.close()


if __name__ == "__main__":
    load()