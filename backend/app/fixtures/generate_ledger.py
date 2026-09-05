"""
Generates synthetic milestones for the Transparency Ledger.

THIS DATA IS NOT REAL. No row corresponds to any actual applicant.

Stage gaps follow documented figures in FINAL_PROBLEM_DISCOVERY_REPORT.md s4 -
roughly three months from application to sanction, one more month to
disbursement - so the shape is plausible. The numbers themselves are generated.

REJECT_RATE is invented. Report s7/G2 establishes that no Indian government
credit scheme publishes a rejection figure - there is no denominator anywhere,
including for the government. It exists here only so the state machine has
terminal states. It must NEVER be surfaced in the UI as a rejection rate.
"""
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

random.seed(26092)          # identical output every run - no demo surprises

# The twelve districts with channels. Census 2011 codes.
DISTRICTS = ["572", "583", "555", "577", "521", "505",
             "603", "632", "41", "49", "439", "444"]

SCHEMES = ["nsfdc.suvidha", "nsfdc.micro_credit",
           "nsfdc.mahila_samriddhi", "nsfdc.laghu_vyavsay"]

GAPS = {
    "DOCS_SUBMITTED": (5, 30),
    "VERIFIED": (10, 45),
    "COMMITTEE": (15, 60),
    "SANCTIONED": (5, 40),
    "DISBURSED": (15, 60),
}
STALL_RATE = 0.22
REJECT_RATE = 0.28


def generate(n: int = 200) -> list[dict]:
    rows: list[dict] = []
    reported_at = datetime.now(timezone.utc).isoformat()
    window_start = date(2025, 10, 1)

    for i in range(n):
        ref = f"syn-{i:04d}"
        district = random.choice(DISTRICTS)
        scheme = random.choice(SCHEMES)
        cursor = window_start + timedelta(days=random.randint(0, 240))

        def add(stage: str, gap: int) -> None:
            nonlocal cursor
            cursor += timedelta(days=gap)
            rows.append({
                "application_ref": ref,
                "district_code": district,
                "scheme_id": scheme,
                "stage": stage,
                "occurred_on": cursor.isoformat(),
                "reported_by": "operator",
                "reported_at": reported_at,
            })

        add("APPLIED", 0)
        add("DOCS_SUBMITTED", random.randint(*GAPS["DOCS_SUBMITTED"]))
        if random.random() < STALL_RATE:
            continue

        add("VERIFIED", random.randint(*GAPS["VERIFIED"]))
        add("COMMITTEE", random.randint(*GAPS["COMMITTEE"]))
        if random.random() < REJECT_RATE:
            add("REJECTED", random.randint(5, 30))
            continue

        add("SANCTIONED", random.randint(*GAPS["SANCTIONED"]))
        if random.random() < 0.85:
            add("DISBURSED", random.randint(*GAPS["DISBURSED"]))

    return rows


if __name__ == "__main__":
    out = Path(__file__).parent / "ledger_milestones.json"
    data = generate(200)
    out.write_text(json.dumps(data, indent=2))
    print(f"Wrote {len(data)} synthetic rows to {out}")